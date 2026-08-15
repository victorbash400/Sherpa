import AppKit
import CoreImage
import Foundation
import ImageIO
import ScreenCaptureKit
import UniformTypeIdentifiers

struct CaptureTarget {
    let app: String?
    let pid: pid_t?
    let windowID: CGWindowID?
    let title: String?

    init(arguments: [String]) {
        app = arguments.value(after: "--app")
        pid = arguments.value(after: "--pid").flatMap(Int32.init)
        windowID = arguments.value(after: "--window-id").flatMap(UInt32.init)
        title = arguments.value(after: "--window-title")
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

final class FrameOutput: NSObject, SCStreamOutput, SCStreamDelegate {
    private let context = CIContext(options: [.cacheIntermediates: false])
    private let output = FileHandle.standardOutput
    private var writing = false

    func stream(
        _ stream: SCStream,
        didOutputSampleBuffer sampleBuffer: CMSampleBuffer,
        of outputType: SCStreamOutputType
    ) {
        guard outputType == .screen,
              !writing,
              sampleBuffer.isValid,
              let pixelBuffer = sampleBuffer.imageBuffer else { return }
        writing = true
        defer { writing = false }

        let image = CIImage(cvPixelBuffer: pixelBuffer)
        guard let cgImage = context.createCGImage(image, from: image.extent),
              let data = jpegData(from: cgImage) else { return }
        writePacket(data, to: output)
    }

    func stream(_ stream: SCStream, didStopWithError error: any Error) {
        FileHandle.standardError.write(Data("\(error)\n".utf8))
        exit(EXIT_FAILURE)
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
            [kCGImageDestinationLossyCompressionQuality: 0.62] as CFDictionary
        )
        guard CGImageDestinationFinalize(destination) else { return nil }
        return data as Data
    }
}

@main
struct WindowCapture {
    static func main() async {
        do {
            _ = NSApplication.shared
            let target = CaptureTarget(arguments: CommandLine.arguments)
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

            let metadata = try JSONEncoder().encode(WindowMetadata(
                x: window.frame.origin.x,
                y: window.frame.origin.y,
                width: window.frame.width,
                height: window.frame.height
            ))
            writePacket(metadata, to: FileHandle.standardOutput)

            let configuration = SCStreamConfiguration()
            let scale = min(1, 720 / max(window.frame.width, 1))
            configuration.width = max(1, Int(window.frame.width * scale))
            configuration.height = max(1, Int(window.frame.height * scale))
            configuration.minimumFrameInterval = CMTime(value: 1, timescale: 4)
            configuration.queueDepth = 3
            configuration.showsCursor = false
            configuration.capturesAudio = false

            let output = FrameOutput()
            let stream = SCStream(
                filter: SCContentFilter(desktopIndependentWindow: window),
                configuration: configuration,
                delegate: output
            )
            try stream.addStreamOutput(
                output,
                type: .screen,
                sampleHandlerQueue: DispatchQueue(label: "sherpa.window.capture")
            )
            try await stream.startCapture()
            Task.detached {
                _ = FileHandle.standardInput.readDataToEndOfFile()
                exit(EXIT_SUCCESS)
            }
            await withCheckedContinuation { (_: CheckedContinuation<Void, Never>) in }
        } catch {
            FileHandle.standardError.write(Data("\(error)\n".utf8))
            exit(EXIT_FAILURE)
        }
    }

    static func preferredWindow(_ lhs: SCWindow, _ rhs: SCWindow) -> Bool {
        if lhs.isOnScreen != rhs.isOnScreen { return lhs.isOnScreen }
        return lhs.frame.width * lhs.frame.height > rhs.frame.width * rhs.frame.height
    }
}

struct WindowMetadata: Encodable {
    let type = "metadata"
    let x: Double
    let y: Double
    let width: Double
    let height: Double
}

func writePacket(_ data: Data, to output: FileHandle) {
    var length = UInt32(data.count).bigEndian
    output.write(Data(bytes: &length, count: MemoryLayout<UInt32>.size))
    output.write(data)
}

enum CaptureError: LocalizedError {
    case windowNotFound

    var errorDescription: String? {
        "The assigned window is not available for preview."
    }
}

extension Array where Element == String {
    func value(after flag: String) -> String? {
        guard let index = firstIndex(of: flag), indices.contains(index + 1) else { return nil }
        return self[index + 1]
    }
}
