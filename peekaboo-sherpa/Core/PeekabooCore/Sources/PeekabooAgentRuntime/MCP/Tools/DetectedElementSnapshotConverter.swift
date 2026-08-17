import PeekabooAutomationKit

enum DetectedElementSnapshotConverter {
    static func convert(_ detected: [DetectedElement]) -> [UIElement] {
        let childrenByParent = Dictionary(grouping: detected, by: { $0.attributes["parentId"] })
        return detected.map { element in
            UIElement(
                id: element.id,
                elementId: element.id,
                role: element.attributes["role"] ?? element.type.rawValue,
                title: element.attributes["title"],
                label: element.label,
                value: element.value,
                description: element.attributes["description"],
                help: element.attributes["help"],
                roleDescription: element.attributes["roleDescription"],
                identifier: element.attributes["identifier"],
                confidence: element.attributes["confidence"].flatMap(Double.init),
                frame: element.bounds,
                isActionable: element.isActionable,
                isEnabled: element.knownIsEnabled,
                isSelected: element.isSelected,
                isValueSettable: element.isValueSettable,
                parentId: element.attributes["parentId"],
                children: childrenByParent[element.id, default: []].map(\.id),
                keyboardShortcut: element.attributes["keyboardShortcut"])
        }
    }
}
