import Foundation
import MCP
import PeekabooAutomation
import PeekabooFoundation
import TachikomaMCP

/// Returns a compact, cross-application catalog of agent-visible macOS surfaces.
public struct SurfacesTool: MCPTool {
    private let context: MCPToolContext

    public let name = "surfaces"

    public var description: String {
        """
        Discovers visible macOS windows, dialogs, and sheets without reading their full UI trees.

        Use this before observing a multi-window application or choosing between several active
        applications. Each result has an opaque surface ID plus the exact PID and CoreGraphics
        window ID accepted by `see`, `inspect_ui`, and interaction tools.
        """
    }

    public var inputSchema: Value {
        SchemaBuilder.object(
            properties: [
                "apps": SchemaBuilder.array(
                    items: SchemaBuilder.string(),
                    description: "Optional app names, bundle IDs, or PID selectors. Omit to inspect windowed apps."),
                "include_hidden": SchemaBuilder.boolean(
                    description: "Include hidden applications and off-screen windows.",
                    default: false),
            ],
            required: [])
    }

    public init(context: MCPToolContext = .shared) {
        self.context = context
    }

    @MainActor
    public func execute(arguments: ToolArguments) async throws -> ToolResponse {
        let requestedApps = arguments.getStringArray("apps") ?? []
        let includeHidden = arguments.getBool("include_hidden") ?? false
        let listed = try await self.context.applications.listApplications().data.applications
        let eligible = listed.filter { app in
            guard app.activationPolicy != .prohibited else { return false }
            guard includeHidden || !app.isHidden else { return false }
            guard app.windowCount > 0 || app.windowIDs?.isEmpty == false else { return false }
            if requestedApps.isEmpty { return true }
            return requestedApps.contains { ApplicationIdentifierMatcher.matches(app, identifier: $0) }
        }

        var surfaces: [DiscoveredSurface] = []
        var warnings: [String] = []
        for app in eligible {
            do {
                let output = try await self.context.applications.listWindows(
                    for: "PID:\(app.processIdentifier)",
                    timeout: nil)
                surfaces.append(contentsOf: output.data.windows.compactMap { window in
                    guard includeHidden || (!window.isOffScreen && !window.isMinimized) else { return nil }
                    guard window.alpha > 0.01, !window.isExcludedFromWindowsMenu else { return nil }
                    guard !window.title.isEmpty || window.isMainWindow || window.isKeyWindow == true ||
                        DiscoveredSurface.kind(for: window.subrole) != "window"
                    else { return nil }
                    return DiscoveredSurface(app: app, window: window)
                })
            } catch {
                warnings.append("\(app.name): \(error.localizedDescription)")
            }
        }

        surfaces = Self.attachTransientSurfaces(surfaces)
            .sorted { lhs, rhs in
                if lhs.isFocused != rhs.isFocused { return lhs.isFocused }
                if lhs.appName != rhs.appName { return lhs.appName < rhs.appName }
                return lhs.windowIndex < rhs.windowIndex
            }

        let catalog: Value = .object([
            "surface_count": .int(surfaces.count),
            "surfaces": .array(surfaces.map(\.value)),
            "warnings": .array(warnings.map(Value.string)),
        ])
        let catalogText = try Self.catalogJSON(surfaces: surfaces, warnings: warnings)
        return ToolResponse(
            content: [.text(text: catalogText, annotations: nil, _meta: nil)],
            structuredContent: catalog)
    }

    private static func attachTransientSurfaces(_ surfaces: [DiscoveredSurface]) -> [DiscoveredSurface] {
        surfaces.map { surface in
            guard surface.kind != "window" else { return surface }
            let center = CGPoint(x: surface.bounds.midX, y: surface.bounds.midY)
            let parent = surfaces
                .filter { $0.pid == surface.pid && $0.kind == "window" && $0.bounds.contains(center) }
                .min { $0.bounds.width * $0.bounds.height < $1.bounds.width * $1.bounds.height }
            return surface.withParent(parent?.surfaceID)
        }
    }

    private static func catalogJSON(surfaces: [DiscoveredSurface], warnings: [String]) throws -> String {
        let data = try JSONSerialization.data(
            withJSONObject: [
                "surface_count": surfaces.count,
                "surfaces": surfaces.map(\.dictionary),
                "warnings": warnings,
            ],
            options: [.sortedKeys])
        guard let text = String(data: data, encoding: .utf8) else {
            throw PeekabooError.operationError(message: "Failed to encode the surface catalog")
        }
        return text
    }

}

private struct DiscoveredSurface {
    let surfaceID: String
    let appName: String
    let bundleID: String?
    let pid: Int32
    let processStartIdentity: UInt64?
    let windowID: Int
    let title: String
    let kind: String
    let bounds: CGRect
    let isFocused: Bool
    let isMinimized: Bool
    let isOffScreen: Bool
    let windowIndex: Int
    let parentSurfaceID: String?

    init(app: ServiceApplicationInfo, window: ServiceWindowInfo, parentSurfaceID: String? = nil) {
        self.surfaceID = "surface_\(app.processIdentifier)_\(window.windowID)"
        self.appName = app.name
        self.bundleID = app.bundleIdentifier
        self.pid = app.processIdentifier
        self.processStartIdentity = app.processStartIdentity
        self.windowID = window.windowID
        self.title = window.title
        self.kind = Self.kind(for: window.subrole)
        self.bounds = window.bounds
        self.isFocused = window.isKeyWindow == true || window.isFrontmost == true
        self.isMinimized = window.isMinimized
        self.isOffScreen = window.isOffScreen
        self.windowIndex = window.index
        self.parentSurfaceID = parentSurfaceID
    }

    private init(copying surface: Self, parentSurfaceID: String?) {
        self.surfaceID = surface.surfaceID
        self.appName = surface.appName
        self.bundleID = surface.bundleID
        self.pid = surface.pid
        self.processStartIdentity = surface.processStartIdentity
        self.windowID = surface.windowID
        self.title = surface.title
        self.kind = surface.kind
        self.bounds = surface.bounds
        self.isFocused = surface.isFocused
        self.isMinimized = surface.isMinimized
        self.isOffScreen = surface.isOffScreen
        self.windowIndex = surface.windowIndex
        self.parentSurfaceID = parentSurfaceID
    }

    func withParent(_ parentSurfaceID: String?) -> Self {
        Self(copying: self, parentSurfaceID: parentSurfaceID)
    }

    var value: Value {
        .object([
            "surface_id": .string(self.surfaceID),
            "kind": .string(self.kind),
            "app": .string(self.appName),
            "bundle_id": self.bundleID.map(Value.string) ?? .null,
            "pid": .int(Int(self.pid)),
            "process_start_identity": self.processStartIdentity.map { .string(String($0)) } ?? .null,
            "window_id": .int(self.windowID),
            "title": .string(self.title),
            "bounds": .object([
                "x": .double(Double(self.bounds.origin.x)),
                "y": .double(Double(self.bounds.origin.y)),
                "width": .double(Double(self.bounds.width)),
                "height": .double(Double(self.bounds.height)),
            ]),
            "focused": .bool(self.isFocused),
            "minimized": .bool(self.isMinimized),
            "off_screen": .bool(self.isOffScreen),
            "parent_surface_id": self.parentSurfaceID.map(Value.string) ?? .null,
        ])
    }

    var dictionary: [String: Any] {
        var result: [String: Any] = [
            "surface_id": self.surfaceID,
            "kind": self.kind,
            "app": self.appName,
            "pid": Int(self.pid),
            "window_id": self.windowID,
            "title": self.title,
            "bounds": [
                "x": self.bounds.origin.x,
                "y": self.bounds.origin.y,
                "width": self.bounds.width,
                "height": self.bounds.height,
            ],
        ]
        if self.isFocused { result["focused"] = true }
        if let parentSurfaceID = self.parentSurfaceID {
            result["parent_surface_id"] = parentSurfaceID
        }
        return result
    }

    static func kind(for subrole: String?) -> String {
        switch subrole {
        case "AXSheet": "sheet"
        case "AXDialog", "AXSystemDialog", "AXAlert": "dialog"
        default: "window"
        }
    }
}
