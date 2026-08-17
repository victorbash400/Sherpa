import CoreGraphics
import Testing
@testable import PeekabooAutomationKit

struct BackgroundInputDriverWindowRoutingTests {
    @Test
    func `Exact window lookup includes a window on another Space`() throws {
        var observedOptions: CGWindowListOption?
        var observedRelativeWindow: CGWindowID?
        let candidates = BackgroundInputDriver
            .mouseWindowRouteCandidates(exactWindowID: 42) { options, relativeToWindow in
                observedOptions = options
                observedRelativeWindow = relativeToWindow
                return [[
                    kCGWindowNumber as String: 42,
                    kCGWindowOwnerPID as String: 123,
                    kCGWindowLayer as String: 0,
                    kCGWindowBounds as String: [
                        "X": 0,
                        "Y": 0,
                        "Width": 200,
                        "Height": 200,
                    ],
                    kCGWindowIsOnscreen as String: false,
                ]]
            }

        let resolved = try BackgroundInputDriver.resolveTargetWindowID(
            at: CGPoint(x: 50, y: 50),
            targetProcessIdentifier: 123,
            exactWindowID: 42,
            candidates: candidates)

        #expect(observedOptions?.contains(.optionIncludingWindow) == true)
        #expect(observedOptions?.contains(.optionOnScreenOnly) == false)
        #expect(observedRelativeWindow == 42)
        #expect(resolved == 42)
    }

    @Test
    func `Exact window wins over an overlapping sibling window`() throws {
        let candidates = [
            Self.candidate(windowID: 99, processIdentifier: 123, bounds: CGRect(x: 0, y: 0, width: 200, height: 200)),
            Self.candidate(windowID: 42, processIdentifier: 123, bounds: CGRect(x: 0, y: 0, width: 200, height: 200)),
        ]

        let resolved = try BackgroundInputDriver.resolveTargetWindowID(
            at: CGPoint(x: 50, y: 50),
            targetProcessIdentifier: 123,
            exactWindowID: 42,
            candidates: candidates)

        #expect(resolved == 42)
    }

    @Test
    func `Exact window rejects PID reuse`() {
        let candidates = [
            Self.candidate(windowID: 42, processIdentifier: 999, bounds: CGRect(x: 0, y: 0, width: 200, height: 200)),
        ]

        #expect(throws: (any Error).self) {
            try BackgroundInputDriver.resolveTargetWindowID(
                at: CGPoint(x: 50, y: 50),
                targetProcessIdentifier: 123,
                exactWindowID: 42,
                candidates: candidates)
        }
    }

    @Test
    func `Exact window rejects a point outside current bounds`() {
        let candidates = [
            Self.candidate(windowID: 42, processIdentifier: 123, bounds: CGRect(x: 0, y: 0, width: 20, height: 20)),
        ]

        #expect(throws: (any Error).self) {
            try BackgroundInputDriver.resolveTargetWindowID(
                at: CGPoint(x: 50, y: 50),
                targetProcessIdentifier: 123,
                exactWindowID: 42,
                candidates: candidates)
        }
    }

    private static func candidate(
        windowID: CGWindowID,
        processIdentifier: pid_t,
        bounds: CGRect) -> BackgroundInputDriver.MouseWindowRouteCandidate
    {
        BackgroundInputDriver.MouseWindowRouteCandidate(
            windowID: windowID,
            processIdentifier: processIdentifier,
            layer: 0,
            bounds: bounds)
    }
}
