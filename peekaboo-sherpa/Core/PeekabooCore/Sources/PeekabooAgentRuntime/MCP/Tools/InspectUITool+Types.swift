import MCP
import PeekabooAutomationKit
import PeekabooFoundation
import TachikomaMCP

struct InspectUIRequest {
    let appTarget: String?
    let windowIDValue: Value?
    let snapshotId: String?
    let webFocus: Bool
    let query: String?
    let maxResults: Int
    let traversalBudget: AXTraversalBudget

    init(arguments: ToolArguments) throws {
        self.appTarget = arguments.getString("app_target")
        self.windowIDValue = arguments.getValue(for: "window_id")
        self.snapshotId = arguments.getString("snapshot")
        self.webFocus = arguments.getBool("web_focus") ?? false
        self.query = arguments.getString("query")?.trimmingCharacters(in: .whitespacesAndNewlines)
        self.maxResults = try Self.positiveInt("max_results", in: arguments) ?? 120
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

@MainActor
struct InspectUISummaryBuilder {
    private static let maxFieldLength = 240

    let snapshot: UISnapshot
    let result: ElementDetectionResult
    let target: ObservationTargetArgument
    let query: String?
    let maxResults: Int

    func build() async -> String {
        var lines = self.headerLines()
        await lines.append(contentsOf: self.metadataLines())
        lines.append("Elements found: \(self.result.elements.all.count)")
        if let query, !query.isEmpty {
            lines.append("Query: \(query)")
            lines.append("Matching elements: \(self.matchingElements().count)")
        }
        if self.result.metadata.method.contains("cached") {
            lines.append("(Result from cached accessibility tree)")
        }
        lines.append(contentsOf: self.truncationWarningLines())
        lines.append("")
        lines.append(contentsOf: self.elementSection())
        lines.append("")
        lines.append("Use element IDs with click, type, and other interaction commands.")
        lines.append("If text looks incomplete, use `see` for a screenshot-based observation.")
        return lines.joined(separator: "\n")
    }

    private func headerLines() -> [String] {
        [
            "UI Text Inspection",
            "Snapshot ID: \(self.snapshot.id)",
        ]
    }

    private func metadataLines() async -> [String] {
        var lines: [String] = []
        if let appName = self.result.metadata.windowContext?.applicationName {
            lines.append("Application: \(appName)")
        }
        if let windowTitle = self.result.metadata.windowContext?.windowTitle {
            lines.append("Window: \(windowTitle)")
        }
        return lines
    }

    private func elementSection() -> [String] {
        let elements = self.result.elements.all
        guard !elements.isEmpty else {
            return ["No accessible UI elements found. Try `see` for screenshot-based detection."]
        }

        let matches = self.matchingElements()
        let renderedMatches = Array(matches.prefix(self.maxResults))
        let renderedElements = self.elementsIncludingAncestors(of: renderedMatches, in: elements)
        let omittedCount = matches.count - renderedMatches.count
        var lines = ["UI Elements (hierarchical):"]
        lines.append(contentsOf: renderedElements.map(self.describeElement))
        if omittedCount > 0 {
            lines.append("")
            lines.append(
                "\(omittedCount) additional elements omitted from text output. " +
                    "Use a narrower query if you need different context.")
        }
        return lines
    }

    private func truncationWarningLines() -> [String] {
        guard let truncationInfo = self.result.metadata.truncationInfo, truncationInfo.isTruncated else {
            return []
        }
        return [truncationInfo.automationToolRemediationMessage(
            budget: self.result.metadata.windowContext?.traversalBudget)]
    }

    private func matchingElements() -> [DetectedElement] {
        guard let query, !query.isEmpty else { return self.result.elements.all }
        let terms = query.lowercased().split(whereSeparator: \.isWhitespace).map(String.init)
        return self.result.elements.all.filter { element in
            let haystack = ([element.type.rawValue] + [element.label, element.value].compactMap { $0 } +
                Array(element.attributes.values))
                .joined(separator: " ")
                .lowercased()
            return terms.allSatisfy(haystack.contains)
        }
    }

    private func elementsIncludingAncestors(
        of matches: [DetectedElement],
        in allElements: [DetectedElement]) -> [DetectedElement]
    {
        let byID = Dictionary(uniqueKeysWithValues: allElements.map { ($0.id, $0) })
        var included = Set(matches.map(\.id))
        for match in matches {
            var parentID = match.attributes["parentId"]
            while let current = parentID, let parent = byID[current] {
                included.insert(current)
                parentID = parent.attributes["parentId"]
            }
        }
        let includedElements = allElements.filter { included.contains($0.id) }
        let includedIDs = Set(includedElements.map(\.id))
        let childrenByParent = Dictionary(grouping: includedElements) { element in
            guard let parentID = element.attributes["parentId"], includedIDs.contains(parentID) else { return "" }
            return parentID
        }
        var ordered: [DetectedElement] = []
        func appendSubtree(parentID: String) {
            for element in childrenByParent[parentID, default: []] {
                ordered.append(element)
                appendSubtree(parentID: element.id)
            }
        }
        appendSubtree(parentID: "")
        return ordered
    }

    private func describeElement(_ element: DetectedElement) -> String {
        let depth = Int(element.attributes["depth"] ?? "0") ?? 0
        var parts = [String(repeating: "  ", count: depth) + element.id]
        parts.append("[\(element.type.rawValue)]")
        if let label = self.clipped(element.label) {
            parts.append("\"\(label)\"")
        }
        let sizeText = "size \(Int(element.bounds.width))x\(Int(element.bounds.height))"
        parts.append("at (\(Int(element.bounds.origin.x)), \(Int(element.bounds.origin.y))) \(sizeText)")
        if let value = self.clipped(element.value) {
            parts.append("value: \"\(value)\"")
        }
        if let desc = self.clipped(element.attributes["description"]) {
            parts.append("desc: \"\(desc)\"")
        }
        if let help = self.clipped(element.attributes["help"]) {
            parts.append("help: \"\(help)\"")
        }
        if let shortcut = self.clipped(element.attributes["keyboardShortcut"]) {
            parts.append("shortcut: \(shortcut)")
        }
        if let identifier = self.clipped(element.attributes["identifier"]) {
            parts.append("identifier: \(identifier)")
        }
        if let isValueSettable = element.isValueSettable {
            parts.append(isValueSettable ? "[value settable]" : "[value read-only]")
        }
        if element.isActionable {
            parts.append("[actionable]")
        }
        if element.knownIsEnabled == false {
            parts.append("[not actionable]")
        }
        return parts.joined(separator: " - ")
    }

    private func clipped(_ value: String?) -> String? {
        guard let value, !value.isEmpty else { return nil }
        guard value.count > Self.maxFieldLength else { return value }
        let index = value.index(value.startIndex, offsetBy: Self.maxFieldLength)
        return String(value[..<index]) + "..."
    }
}
