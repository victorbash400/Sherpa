import CoreGraphics
import PeekabooFoundation
import Testing
@testable import PeekabooAutomationKit

@MainActor
struct DialogFileExpansionTargetTests {
    @Test
    func `Open panel confirmation succeeds only after the retained dialog disappears`() {
        let fallback = DesktopActionOutcome.suspectedNoop(
            delivery: DialogService.foregroundKeyboardDelivery,
            unitCount: .one)

        #expect(DialogService.fileDialogClosureFailure(
            presence: .absent,
            fallbackOutcome: fallback) == nil)
        #expect(DialogService.fileDialogClosureFailure(
            presence: .present,
            fallbackOutcome: fallback)?.message.contains("remained open") == true)
        #expect(DialogService.fileDialogClosureFailure(
            presence: .unreadable,
            fallbackOutcome: fallback)?.message.contains("could not be verified") == true)
    }

    @Test
    func `Verified expansion refreshes bounds for the same window generation`() throws {
        let retained = try Self.target(bounds: CGRect(x: 10, y: 20, width: 300, height: 200))
        let expanded = try Self.target(bounds: CGRect(x: 10, y: 20, width: 600, height: 500))

        let refreshed = try DialogService.refreshFileDialogTargetAfterVerifiedExpansion(
            expanded,
            retained: retained)

        #expect(refreshed == expanded)
        #expect(refreshed.bounds == CGRect(x: 10, y: 20, width: 600, height: 500))
        #expect(refreshed.identity.processIdentity == retained.identity.processIdentity)
        #expect(refreshed.identity.windowID == retained.identity.windowID)
    }

    @Test
    func `Expansion refresh rejects a different window or process generation`() throws {
        let retained = try Self.target(bounds: CGRect(x: 10, y: 20, width: 300, height: 200))
        let replacements = try [
            Self.target(
                bounds: CGRect(x: 10, y: 20, width: 600, height: 500),
                windowID: 74),
            Self.target(
                bounds: CGRect(x: 10, y: 20, width: 600, height: 500),
                processStartIdentity: 9002),
        ]

        for replacement in replacements {
            do {
                _ = try DialogService.refreshFileDialogTargetAfterVerifiedExpansion(
                    replacement,
                    retained: retained)
                Issue.record("Expected expansion target replacement to fail closed")
            } catch let failure as DesktopActionFailure {
                #expect(failure.outcome.state == .refused)
                #expect(failure.outcome.refusalReason == .targetUnavailable)
                #expect(failure.outcome.dispatchState == .none)
                #expect(failure.outcome.retrySafety == .safe)
            }
        }
    }

    @Test
    func `Automatic navigation expansion refreshes target before later exact checks`() throws {
        let retained = try Self.target(bounds: CGRect(x: 10, y: 20, width: 300, height: 200))
        let expanded = try Self.target(bounds: CGRect(x: 10, y: 20, width: 600, height: 500))

        let refreshed = try DialogService.fileDialogTargetAfterNavigation(
            expanded,
            retained: retained,
            disposition: .refreshAfterExpansion)
        let checked = try DialogService.fileDialogTargetAfterNavigation(
            expanded,
            retained: refreshed,
            disposition: .unchanged)

        #expect(refreshed == expanded)
        #expect(checked == expanded)
    }

    @Test
    func `Navigation refreshes resized panel owned by the same window generation`() throws {
        let retained = try Self.target(bounds: CGRect(x: 10, y: 20, width: 300, height: 200))
        let navigated = try Self.target(bounds: CGRect(x: 8, y: 18, width: 640, height: 520))

        let refreshed = try DialogService.fileDialogTargetAfterNavigation(
            navigated,
            retained: retained,
            disposition: .unchanged)

        #expect(refreshed == navigated)
        #expect(refreshed.bounds == navigated.bounds)
    }

    @Test
    func `Navigation still rejects a different window generation`() throws {
        let retained = try Self.target(bounds: CGRect(x: 10, y: 20, width: 300, height: 200))
        let replacement = try Self.target(
            bounds: CGRect(x: 10, y: 20, width: 300, height: 200),
            windowID: 74)

        #expect(throws: (any Error).self) {
            try DialogService.fileDialogTargetAfterNavigation(
                replacement,
                retained: retained,
                disposition: .unchanged)
        }
    }

    private static func target(
        bounds: CGRect,
        windowID: Int = 73,
        processStartIdentity: UInt64 = 9001) throws -> UIAutomationTarget.ExactWindow
    {
        try UIAutomationTarget.ExactWindow(
            identity: WindowMutationIdentity(
                windowID: windowID,
                ownerProcessIdentifier: 42,
                ownerProcessStartIdentity: processStartIdentity,
                capturedBounds: bounds),
            bounds: bounds)
    }
}
