import AppKit
import CoreImage
import Foundation
import ImageIO
import ScreenCaptureKit
import UniformTypeIdentifiers

private let packetLock = NSLock()

struct CaptureTarget: Decodable {
    let app: String?
    let pid: pid_t?
    let windowID: CGWindowID?
    let title: String?

    enum CodingKeys: String, CodingKey {
        case app, pid
        case windowID = "window_id"
        case title = "window_title"
    }

    func matches(_ window: SCWindow) -> Bool {
        if let windowID, window.windowID != windowID { return false }
        if let pid, window.owningApplication?.processID != pid { return false }
        if let app {
            let owner = window.owningApplication
            let matchesName = owner?.applicationName.localizedCaseInsensitiveContains(app) == true
            let matchesBundle = owner?.bundleIdentifier.caseInsensitiveCompare(app) == .orderedSame
            if !matchesName && !matchesBundle { return false }
        }
        if let title, window.title?.localizedCaseInsensitiveContains(title) != true { return false }
        return true
    }
}

struct CaptureCommand: Decodable {
    let action: String
    let taskID: String?
    let target: CaptureTarget?

    enum CodingKeys: String, CodingKey {
        case action, target
        case taskID = "task_id"
    }
}

final class FrameOutput: NSObject, SCStreamOutput, SCStreamDelegate {
    private let context = CIContext(options: [.cacheIntermediates: false])
    private let lock = NSLock()
    private var taskID: String?
    private var writing = false

    func select(taskID: String?) {
        lock.withLock { self.taskID = taskID }
    }

    func stream(
        _ stream: SCStream,
        didOutputSampleBuffer sampleBuffer: CMSampleBuffer,
        of outputType: SCStreamOutputType
    ) {
        guard outputType == .screen,
              sampleBuffer.isValid,
              let pixelBuffer = sampleBuffer.imageBuffer else { return }
        let selected = lock.withLock { () -> String? in
            guard let taskID, !writing else { return nil }
            writing = true
            return taskID
        }
        guard let selected else { return }
        defer { lock.withLock { writing = false } }

        let image = CIImage(cvPixelBuffer: pixelBuffer)
        guard let cgImage = context.createCGImage(image, from: image.extent),
              let data = jpegData(from: cgImage) else { return }
        writeFrame(data, taskID: selected)
    }

    func stream(_ stream: SCStream, didStopWithError error: any Error) {
        writeEvent(["type": "stream_error", "message": error.localizedDescription])
    }

    private func jpegData(from image: CGImage) -> Data? {
        let data = NSMutableData()
        guard let destination = CGImageDestinationCreateWithData(
            data,
            UTType.jpeg.identifier as CFString,
            1,
            nil
        ) else { return nil }
        CGImageDestinationAddImage(
            destination,
            image,
            [kCGImageDestinationLossyCompressionQuality: 0.58] as CFDictionary
        )
        guard CGImageDestinationFinalize(destination) else { return nil }
        return data as Data
    }
}

@main
struct WindowCapture {
    static func main() async {
        _ = NSApplication.shared
        let output = FrameOutput()
        var stream: SCStream?

        while let line = readLine() {
            do {
                let command = try JSONDecoder().decode(CaptureCommand.self, from: Data(line.utf8))
                switch command.action {
                case "switch":
                    guard let taskID = command.taskID, let target = command.target else {
                        throw CaptureError.invalidCommand
                    }
                    let content = try await SCShareableContent.excludingDesktopWindows(
                        false,
                        onScreenWindowsOnly: false
                    )
                    guard let window = content.windows
                        .filter(target.matches)
                        .sorted(by: preferredWindow)
                        .first else {
                        throw CaptureError.windowNotFound
                    }
                    let filter = SCContentFilter(desktopIndependentWindow: window)
                    let configuration = captureConfiguration(for: window)
                    output.select(taskID: nil)
                    if let stream {
                        try await stream.updateContentFilter(filter)
                        try await stream.updateConfiguration(configuration)
                    } else {
                        let nextStream = SCStream(filter: filter, configuration: configuration, delegate: output)
                        try nextStream.addStreamOutput(
                            output,
                            type: .screen,
                            sampleHandlerQueue: DispatchQueue(label: "sherpa.window.capture")
                        )
                        try await nextStream.startCapture()
                        stream = nextStream
                    }
                    output.select(taskID: taskID)
                    writeEvent([
                        "type": "metadata",
                        "task_id": taskID,
                        "x": window.frame.origin.x,
                        "y": window.frame.origin.y,
                        "width": window.frame.width,
                        "height": window.frame.height,
                    ])
                case "idle":
                    output.select(taskID: nil)
                    if let stream {
                        try await stream.stopCapture()
                        writeStopped()
                    }
                    stream = nil
                case "stop":
                    output.select(taskID: nil)
                    if let stream { try await stream.stopCapture() }
                    writeStopped()
                    return
                default:
                    throw CaptureError.invalidCommand
                }
            } catch {
                writeEvent(["type": "command_error", "message": error.localizedDescription])
            }
        }

        output.select(taskID: nil)
        if let stream { try? await stream.stopCapture() }
        writeStopped()
    }

    static func captureConfiguration(for window: SCWindow) -> SCStreamConfiguration {
        let configuration = SCStreamConfiguration()
        let scale = min(1, 720 / max(window.frame.width, 1))
        configuration.width = max(1, Int(window.frame.width * scale))
        configuration.height = max(1, Int(window.frame.height * scale))
        configuration.minimumFrameInterval = CMTime(value: 1, timescale: 4)
        configuration.queueDepth = 2
        configuration.showsCursor = false
        configuration.capturesAudio = false
        return configuration
    }

    static func preferredWindow(_ lhs: SCWindow, _ rhs: SCWindow) -> Bool {
        if lhs.isOnScreen != rhs.isOnScreen { return lhs.isOnScreen }
        return lhs.frame.width * lhs.frame.height > rhs.frame.width * rhs.frame.height
    }

    static func writeStopped() {
        writeEvent(["type": "stopped"])
    }
}

func writeEvent(_ event: [String: Any]) {
    guard let data = try? JSONSerialization.data(withJSONObject: event) else { return }
    writePacket(data)
}

func writeFrame(_ image: Data, taskID: String) {
    let identifier = Data(taskID.utf8)
    guard identifier.count <= UInt16.max else { return }
    var length = UInt16(identifier.count).bigEndian
    var packet = Data([0])
    packet.append(Data(bytes: &length, count: MemoryLayout<UInt16>.size))
    packet.append(identifier)
    packet.append(image)
    writePacket(packet)
}

func writePacket(_ data: Data) {
    packetLock.withLock {
        var length = UInt32(data.count).bigEndian
        FileHandle.standardOutput.write(Data(bytes: &length, count: MemoryLayout<UInt32>.size))
        FileHandle.standardOutput.write(data)
    }
}

enum CaptureError: LocalizedError {
    case invalidCommand
    case windowNotFound

    var errorDescription: String? {
        switch self {
        case .invalidCommand: "The preview command was invalid."
        case .windowNotFound: "The assigned window is not available for preview."
        }
    }
}

extension NSLock {
    func withLock<T>(_ operation: () -> T) -> T {
        lock()
        defer { unlock() }
        return operation()
    }
}
