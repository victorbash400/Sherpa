import AppKit
import AXorcist
import Foundation
import PeekabooFoundation

@MainActor
extension DialogService {
    struct FileDialogNavigationResult {
        enum TargetDisposition: Equatable {
            case unchanged
            case refreshAfterExpansion
            case exactFileSelected
        }

        let method: String
        let outcome: DesktopActionOutcome?
        let targetDisposition: TargetDisposition
    }

    func navigateToPath(
        _ filePath: String,
        in dialog: Element,
        ensureExpanded: Bool,
        appName: String?) async throws -> FileDialogNavigationResult
    {
        let expandedPath = (filePath as NSString).expandingTildeInPath
        let targetURL = URL(fileURLWithPath: expandedPath)

        var isDirectory: ObjCBool = false
        let exists = FileManager.default.fileExists(atPath: expandedPath, isDirectory: &isDirectory)

        if exists, !isDirectory.boolValue {
            let exactPath = targetURL.standardizedFileURL.resolvingSymlinksInPath().path
            let outcome = try await self.navigateViaGoToFolder(
                directoryPath: exactPath,
                dialog: dialog,
                appName: appName)
            return FileDialogNavigationResult(
                method: "go_to_exact_file",
                outcome: outcome,
                targetDisposition: .exactFileSelected)
        }

        let directoryPath: String = if exists, isDirectory.boolValue {
            expandedPath
        } else if !targetURL.pathExtension.isEmpty {
            targetURL.deletingLastPathComponent().path
        } else {
            expandedPath
        }

        return try await self.navigateToDirectory(
            directoryPath: directoryPath,
            in: dialog,
            ensureExpanded: ensureExpanded,
            appName: appName)
    }

    func ensureDialogFocus(dialog _: Element, appName: String?) async throws -> DesktopActionOutcome? {
        var sequence = DesktopActionSequenceAccumulator()
        do {
            if let appName, let running = self.runningApplication(matching: appName),
               NSWorkspace.shared.frontmostApplication?.processIdentifier != running.processIdentifier
            {
                try Task.checkCancellation()
                if running.activate(options: [.activateAllWindows]) {
                    sequence.record(.outcome(.dispatchedUnverified(
                        delivery: .init(mechanism: .nativeFramework, mode: .foreground),
                        evidence: .deliveryAccepted,
                        unitCount: .one)))
                }
                try await Task.sleep(nanoseconds: 150_000_000)
            }

            return sequence.successResolution().outcome
        } catch {
            throw Self.preservingFileDialogFailure(error, after: sequence, target: nil)
        }
    }

    func ensureFileDialogExpandedIfNeeded(dialog: Element) async throws -> DesktopActionOutcome? {
        let identifierAttribute = Attribute<String>("AXIdentifier")

        func findDisclosureCandidate(in element: Element) -> Element? {
            DialogTraversal.firstUniqueDepthFirst(
                from: element,
                matching: { current in
                    let identifier = current.attribute(identifierAttribute) ?? ""
                    if identifier.localizedCaseInsensitiveContains("ShowDetails") ||
                        identifier.localizedCaseInsensitiveContains("HideDetails")
                    {
                        return true
                    }

                    let title = (current.title() ?? "").lowercased()
                    if title.contains("show details") || title.contains("hide details") {
                        return true
                    }

                    let description = (current.attribute(Attribute<String>("AXDescription")) ?? "").lowercased()
                    return description.contains("show details") || description.contains("hide details")
                },
                children: { self.sheetFirstTraversalChildren(for: $0) })
        }

        guard let disclosure = findDisclosureCandidate(in: dialog) else { return nil }

        // Never mutate an anonymous disclosure triangle. File panels contain unrelated disclosure controls, and
        // pressing one can replace or dismiss the panel. Expand only when the control explicitly says Show Details.
        let title = (disclosure.title() ?? "").lowercased()
        let description = (disclosure.attribute(Attribute<String>("AXDescription")) ?? "").lowercased()
        let identifier = (disclosure.attribute(identifierAttribute) ?? "").lowercased()
        let shouldClick = title.contains("show details") ||
            description.contains("show details") ||
            identifier.contains("showdetails")
        guard shouldClick else { return nil }

        var sequence = DesktopActionSequenceAccumulator()
        do {
            try sequence.record(.outcome(self.pressOrClick(disclosure, allowGlobalFallback: true)))
            try await Task.sleep(nanoseconds: 250_000_000)
            return sequence.successResolution().outcome
        } catch {
            throw Self.preservingFileDialogFailure(error, after: sequence, target: nil)
        }
    }

    private func navigateToDirectory(
        directoryPath: String,
        in dialog: Element,
        ensureExpanded: Bool,
        appName: String?) async throws -> FileDialogNavigationResult
    {
        var sequence = DesktopActionSequenceAccumulator()
        do {
            let identifierAttribute = Attribute<String>("AXIdentifier")
            let pathFieldIdentifier = "PathTextField"

            func findPathField(in element: Element) -> Element? {
                self.collectTextFields(from: element).first(where: { field in
                    field.attribute(identifierAttribute) == pathFieldIdentifier
                })
            }

            var pathField = findPathField(in: dialog)

            if ensureExpanded {
                if let outcome = try await self.ensureFileDialogExpandedIfNeeded(dialog: dialog) {
                    sequence.record(.outcome(outcome))
                }
                pathField = findPathField(in: dialog)
            }

            if let outcome = try await self.ensureDialogFocus(dialog: dialog, appName: appName) {
                sequence.record(.outcome(outcome))
            }

            let requestedDirectory = URL(fileURLWithPath: directoryPath)
                .standardizedFileURL
                .resolvingSymlinksInPath()
                .path

            var autoExpandedForNavigation = false
            if pathField == nil, !ensureExpanded {
                // When NSSavePanel/NSSOpenPanel is collapsed, Cmd+Shift+G (Go to Folder) is often ignored and the
                // PathTextField isn't in the AX tree. Best effort: expand once before falling back to Go to Folder.
                if let outcome = try await self.ensureFileDialogExpandedIfNeeded(dialog: dialog) {
                    sequence.record(.outcome(outcome))
                }
                autoExpandedForNavigation = true
                pathField = findPathField(in: dialog)
            }

            guard let pathField else {
                if let outcome = try await self.navigateViaGoToFolder(
                    directoryPath: requestedDirectory,
                    dialog: dialog,
                    appName: appName)
                {
                    sequence.record(.outcome(outcome))
                }
                return FileDialogNavigationResult(
                    method: autoExpandedForNavigation ? "go_to_folder+auto_expand" : "go_to_folder",
                    outcome: sequence.successResolution().outcome,
                    targetDisposition: autoExpandedForNavigation ? .refreshAfterExpansion : .unchanged)
            }

            var method = "path_textfield"

            try sequence.record(.outcome(self.focusTextField(pathField)))
            if pathField.isAttributeSettable(named: AXAttributeNames.kAXValueAttribute),
               pathField.setValue(requestedDirectory, forAttribute: AXAttributeNames.kAXValueAttribute)
            {
                sequence.record(.outcome(.dispatchedUnverified(
                    delivery: .init(mechanism: .accessibilityValue, mode: .background),
                    evidence: .deliveryAccepted,
                    unitCount: .one)))
                // Some NSSavePanel implementations don't update AXValue immediately; commit via Return below.
                method = "path_textfield_axvalue"
            } else {
                try sequence.record(.outcome(self.fileDialogGlobalInput(operation: "select the path field") {
                    try self.syntheticInputDriver.hotkey(keys: ["cmd", "a"], holdDuration: 0.05)
                }))
                try await Task.sleep(nanoseconds: 75_000_000)
                try sequence.record(.outcome(self.typeTextValue(requestedDirectory, delay: 5000)))
                method = "path_textfield_typed"
            }
            try sequence.record(.outcome(self.fileDialogGlobalInput(operation: "commit the path field") {
                try self.syntheticInputDriver.tapKey(.return, modifiers: [])
            }))
            try await Task.sleep(nanoseconds: 250_000_000)

            let rawValue = pathField.value() as? String
            if let rawValue, !rawValue.isEmpty {
                let actualDirectory = URL(fileURLWithPath: rawValue)
                    .standardizedFileURL
                    .resolvingSymlinksInPath()
                    .path
                if actualDirectory != requestedDirectory {
                    self.logger.debug("PathTextField mismatch; Go to Folder.")
                    self.logger.debug("requested: \(requestedDirectory), actual: \(actualDirectory)")
                    if let outcome = try await self.navigateViaGoToFolder(
                        directoryPath: requestedDirectory,
                        dialog: dialog,
                        appName: appName)
                    {
                        sequence.record(.outcome(outcome))
                    }
                    method += "+fallback_go_to_folder"
                }
            } else {
                self.logger.debug("PathTextField did not expose an AXValue; falling back to Go to Folder")
                if let outcome = try await self.navigateViaGoToFolder(
                    directoryPath: requestedDirectory,
                    dialog: dialog,
                    appName: appName)
                {
                    sequence.record(.outcome(outcome))
                }
                method += "+fallback_go_to_folder"
            }

            return FileDialogNavigationResult(
                method: method,
                outcome: sequence.successResolution().outcome,
                targetDisposition: autoExpandedForNavigation ? .refreshAfterExpansion : .unchanged)
        } catch {
            throw Self.preservingFileDialogFailure(error, after: sequence, target: nil)
        }
    }

    private func navigateViaGoToFolder(
        directoryPath: String,
        dialog: Element,
        appName: String?) async throws -> DesktopActionOutcome?
    {
        var sequence = DesktopActionSequenceAccumulator()
        do {
            if let outcome = try await self.ensureDialogFocus(dialog: dialog, appName: appName) {
                sequence.record(.outcome(outcome))
            }
            // Cmd+Shift+G is unreliable when the panel is collapsed; try to expand first.
            if let outcome = try await self.ensureFileDialogExpandedIfNeeded(dialog: dialog) {
                sequence.record(.outcome(outcome))
            }
            self.logger.debug("Navigating via Go to Folder (Cmd+Shift+G): \(directoryPath)")

            let keyboardOutcome = try await self.performGoToFolderKeyboardNavigation(directoryPath: directoryPath)
            sequence.record(.outcome(keyboardOutcome))
            // AppKit briefly removes the nested Go-to sheet before republishing the parent file panel.
            // Allow that single transition to settle before exact-target re-resolution; this is not a poll loop.
            try await Task.sleep(nanoseconds: 900_000_000)
            return sequence.successResolution().outcome
        } catch {
            throw Self.preservingFileDialogFailure(error, after: sequence, target: nil)
        }
    }

    func performGoToFolderKeyboardNavigation(directoryPath: String) async throws -> DesktopActionOutcome
    {
        var sequence = DesktopActionSequenceAccumulator()
        do {
            try sequence.record(.outcome(self.fileDialogGlobalInput(operation: "open Go to Folder") {
                try self.syntheticInputDriver.hotkey(keys: ["cmd", "shift", "g"], holdDuration: 0.05)
            }))
            try await Task.sleep(nanoseconds: 250_000_000)
            try sequence.record(.outcome(self.fileDialogGlobalInput(operation: "select Go to Folder text") {
                try self.syntheticInputDriver.hotkey(keys: ["cmd", "a"], holdDuration: 0.05)
            }))
            try await Task.sleep(nanoseconds: 75_000_000)
            try sequence.record(.outcome(self.fileDialogGlobalInput(
                operation: "type the Go to Folder path",
                unitCount: directoryPath.count)
            {
                try self.syntheticInputDriver.type(directoryPath, delayPerCharacter: 0.005)
            }))
            try sequence.record(.outcome(self.fileDialogGlobalInput(operation: "commit Go to Folder") {
                try self.syntheticInputDriver.tapKey(.return, modifiers: [])
            }))
            guard let outcome = sequence.successResolution().outcome else {
                throw DesktopActionFailure.indeterminate(
                    evidence: .completionUnknown,
                    message: "Go to Folder completed without a canonical input outcome.",
                    hint: "Observe the file dialog before retrying.")
            }
            return outcome
        } catch {
            throw Self.preservingFileDialogFailure(error, after: sequence, target: nil)
        }
    }
}
