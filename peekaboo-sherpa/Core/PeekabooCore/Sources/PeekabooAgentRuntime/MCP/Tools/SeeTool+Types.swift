import Foundation
import MCP
import PeekabooAutomationKit
import PeekabooFoundation
import TachikomaMCP

struct SeeRequest {
    let appTarget: String?
    let windowIDValue: Value?
    let path: String?
    let snapshotId: String?
    let annotate: Bool
    let ocr: Bool
    let webFocus: Bool
    let traversalBudget: AXTraversalBudget
    let roi: CaptureRegionOfInterest?

    init(arguments: ToolArguments) throws {
        self.appTarget = arguments.getString("app_target")
        self.windowIDValue = arguments.getValue(for: "window_id")
        self.path = arguments.getString("path")
        self.snapshotId = arguments.getString("snapshot")
        self.annotate = arguments.getBool("annotate") ?? false
        self.ocr = arguments.getBool("ocr") ?? false
        self.webFocus = arguments.getBool("web_focus") ?? false
        if let rawROI = arguments.getString("roi")?.trimmingCharacters(in: .whitespacesAndNewlines),
           !rawROI.isEmpty
        {
            guard self.windowIDValue != nil else {
                throw PeekabooError.invalidInput("roi requires an exact window_id")
            }
            guard self.snapshotId?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty != false else {
                throw PeekabooError.invalidInput("roi requires a fresh snapshot; omit snapshot")
            }
            self.roi = try CaptureRegionOfInterest.parse(rawROI)
        } else {
            self.roi = nil
        }
        self.traversalBudget = try AXTraversalBudget.resolved(
            maxDepth: Self.positiveInt("max_depth", in: arguments),
            maxElementCount: Self.positiveInt("max_elements", in: arguments),
            maxChildrenPerNode: Self.positiveInt("max_children", in: arguments))
    }

    private static func positiveInt(_ key: String, in arguments: ToolArguments) throws -> Int? {
        guard let value = try arguments.validatedInt(key) else { return nil }
        guard value > 0 else {
            throw PeekabooError.invalidInput("\(key) must be a positive integer")
        }
        return value
    }
}

struct ScreenshotOutput {
    let screenshotPath: String
    let annotatedPath: String?
    let imageData: Data
}

struct SeeCaptureArtifact {
    let observationPath: String
    let rawOutputPath: String
    let annotatedOutputPath: String
    private let cleanupDirectory: URL?

    init(requestedPath: String?) throws {
        let hasExplicitPath = requestedPath?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false
        let defaultFileName = "peekaboo-observation-\(UUID().uuidString).png"
        let rawOutputURL = ObservationOutputPathResolver.resolve(
            path: hasExplicitPath ? requestedPath : nil,
            format: .png,
            defaultFileName: defaultFileName)

        self.rawOutputPath = rawOutputURL.path
        self.annotatedOutputPath = ObservationOutputWriter.annotatedScreenshotPath(
            forRawScreenshotPath: rawOutputURL.path)

        if hasExplicitPath {
            let directory = FileManager.default.temporaryDirectory
                .appendingPathComponent("peekaboo-see-response-\(UUID().uuidString)", isDirectory: true)
            try FileManager.default.createDirectory(
                at: directory,
                withIntermediateDirectories: false,
                attributes: [.posixPermissions: 0o700])
            self.observationPath = directory.appendingPathComponent("capture.png").path
            self.cleanupDirectory = directory
        } else {
            self.observationPath = rawOutputURL.path
            self.cleanupDirectory = nil
        }
    }

    func publish(rawData: Data, annotatedData: Data?) throws -> (rawPath: String, annotatedPath: String?) {
        if self.cleanupDirectory != nil {
            let rawURL = URL(fileURLWithPath: self.rawOutputPath)
            try FileManager.default.createDirectory(
                at: rawURL.deletingLastPathComponent(),
                withIntermediateDirectories: true)
            try rawData.write(to: rawURL, options: .atomic)
            if let annotatedData {
                try annotatedData.write(
                    to: URL(fileURLWithPath: self.annotatedOutputPath),
                    options: .atomic)
            }
        }
        return (self.rawOutputPath, annotatedData == nil ? nil : self.annotatedOutputPath)
    }

    func cleanup() {
        guard let cleanupDirectory else { return }
        try? FileManager.default.removeItem(at: cleanupDirectory)
    }

    var observationAnnotatedPath: String {
        ObservationOutputWriter.annotatedScreenshotPath(forRawScreenshotPath: self.observationPath)
    }
}

@MainActor
struct SeeSummaryBuilder {
    private static let maxRenderedElements = 120

    let snapshot: UISnapshot
    let elements: [UIElement]
    let screenshotPath: String
    let truncationInfo: DetectionTruncationInfo?
    let traversalBudget: AXTraversalBudget?

    func build() async -> String {
        var lines = self.headerLines()
        await lines.append(contentsOf: self.metadataLines())
        lines.append("Screenshot: \(self.screenshotPath)")
        lines.append("Elements found: \(self.elements.count)")
        lines.append(contentsOf: self.truncationWarningLines())
        lines.append("")
        lines.append(contentsOf: self.elementSection())
        lines.append("")
        lines.append("Use opaque element IDs for interaction only when the element is marked actionable.")
        return lines.joined(separator: "\n")
    }

    private func headerLines() -> [String] {
        [
            "📸 UI State Captured",
            "Snapshot ID: \(self.snapshot.id)",
        ]
    }

    private func metadataLines() async -> [String] {
        guard let metadata = await self.snapshot.screenshotMetadata else { return [] }
        var lines: [String] = []
        if let appInfo = metadata.applicationInfo {
            lines.append("Application: \(appInfo.name)")
        }
        if let windowInfo = metadata.windowInfo {
            lines.append("Window: \(windowInfo.title)")
        }
        return lines
    }

    private func elementSection() -> [String] {
        let rendered = Array(self.hierarchicalElements().prefix(Self.maxRenderedElements))
        var lines = ["UI Elements (hierarchical):"]
        lines.append(contentsOf: rendered.map(self.describeElement))
        let omitted = self.elements.count - rendered.count
        if omitted > 0 {
            lines.append(
                "\(omitted) additional elements omitted from text output. " +
                    "Use inspect_ui with a query to retrieve the relevant controls and their ancestors.")
        }
        return lines
    }

    private func truncationWarningLines() -> [String] {
        guard let truncationInfo, truncationInfo.isTruncated else { return [] }
        return ["", truncationInfo.automationToolRemediationMessage(budget: self.traversalBudget)]
    }

    private func describeElement(_ element: UIElement) -> String {
        let depth = self.depth(of: element)
        let line = SeeElementTextFormatter.describe(element)
        return String(repeating: "  ", count: depth) + line.dropFirst(2)
    }

    private func hierarchicalElements() -> [UIElement] {
        let ids = Set(self.elements.map(\.id))
        let childrenByParent = Dictionary(grouping: self.elements) { element in
            guard let parentID = element.parentId, ids.contains(parentID) else { return "" }
            return parentID
        }
        var ordered: [UIElement] = []
        func appendSubtree(parentID: String) {
            for element in childrenByParent[parentID, default: []] {
                ordered.append(element)
                appendSubtree(parentID: element.id)
            }
        }
        appendSubtree(parentID: "")
        return ordered
    }

    private func depth(of element: UIElement) -> Int {
        let byID = Dictionary(uniqueKeysWithValues: self.elements.map { ($0.id, $0) })
        var depth = 0
        var parentID = element.parentId
        var visited = Set<String>()
        while let current = parentID, let parent = byID[current], visited.insert(current).inserted {
            depth += 1
            parentID = parent.parentId
        }
        return depth
    }
}
