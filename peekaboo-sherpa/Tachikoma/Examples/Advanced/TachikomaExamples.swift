#!/usr/bin/env swift

import Algorithms
import Foundation
import Tachikoma

@main
struct TachikomaExamples {
    static func main() async {
        print("🕷️  Tachikoma - Modern Swift AI SDK Examples")
        print("=" * 50)

        await self.runAllExamples()
    }

    static func runAllExamples() async {
        // Example 1: Model System
        print("\n📱 Example 1: Type-Safe Model System")
        print("-" * 40)
        demonstrateModelSystem()

        // Example 2: ToolKit System
        print("\n🔧 Example 2: ToolKit System")
        print("-" * 40)
        await demonstrateToolKitSystem()

        // Example 3: Conversation Management
        print("\n💬 Example 3: Conversation Management")
        print("-" * 40)
        demonstrateConversationManagement()

        // Example 4: Usage Tracking
        print("\n📊 Example 4: Usage Tracking")
        print("-" * 40)
        await demonstrateUsageTracking()

        // Example 5: Error Handling
        print("\n⚠️  Example 5: Error Handling")
        print("-" * 40)
        demonstrateErrorHandling()

        // Example 6: Provider Factory
        print("\n🏭 Example 6: Provider Factory")
        print("-" * 40)
        await demonstrateProviderFactory()

        print("\n✅ All examples completed successfully!")
        print("🕷️  Tachikoma - Intelligent • Adaptable • Reliable")
    }
}

// MARK: - Example 1: Model System

extension TachikomaExamples {
    static func demonstrateModelSystem() {
        print("Creating provider-specific models with type safety:")

        // OpenAI models
        let gpt55 = Model.openai(.gpt55)
        let gpt54 = Model.openai(.gpt54)
        let gpt5Mini = Model.openai(.gpt5Mini)

        // Anthropic models
        let opus4 = Model.anthropic(.opus4)
        let sonnet46 = Model.anthropic(.sonnet46)
        let haiku45 = Model.anthropic(.haiku45)

        // Grok models
        let grok43 = Model.grok(.grok43)
        let grokReasoning = Model.grok(.grok420Reasoning)

        // Ollama models
        let llama33 = Model.ollama(.llama3_3)
        let llava = Model.ollama(.llava)

        // Custom endpoints
        let openRouter = Model.openRouter(modelId: "anthropic/claude-sonnet-4.5")
        let customAPI = Model.openaiCompatible(modelId: "gpt-5.5", baseURL: "https://api.azure.com")

        let models = [
            gpt55,
            gpt54,
            gpt5Mini,
            opus4,
            sonnet46,
            haiku45,
            grok43,
            grokReasoning,
            llama33,
            llava,
            openRouter,
            customAPI,
        ]

        for model in models {
            print("  • \(model)")
        }

        print("\nDefault model: \(Model.default)")

        // Model capabilities
        print("\nModel capabilities:")
        print("  • Vision support: \(gpt55.supportsVision)")
        print("  • Tool support: \(opus4.supportsTools)")
        print("  • Streaming support: \(sonnet46.supportsStreaming)")
    }
}

// MARK: - Example 2: ToolKit System

extension TachikomaExamples {
    static func demonstrateToolKitSystem() async {
        print("Creating and using ToolKits:")

        // Weather ToolKit
        let weatherKit = WeatherToolKit()
        print("  • WeatherToolKit with tools: \(weatherKit.toolNames)")

        do {
            let weatherInput = try ToolInput(jsonString: #"{"location": "Tokyo", "units": "celsius"}"#)
            let weatherResult = try await weatherKit.execute(toolNamed: "get_weather", input: weatherInput)
            try print("  • Weather result: \(weatherResult.toJSONString())")
        } catch {
            print("  • Weather error: \(error)")
        }

        // Math ToolKit
        let mathKit = MathToolKit()
        print("  • MathToolKit with tools: \(mathKit.toolNames)")

        do {
            let calcInput = try ToolInput(jsonString: #"{"expression": "2 + 2 * 3"}"#)
            let calcResult = try await mathKit.execute(toolNamed: "calculate", input: calcInput)
            try print("  • Calculation result: \(calcResult.toJSONString())")

            let convertInput =
                try ToolInput(jsonString: #"{"value": 25, "from_unit": "celsius", "to_unit": "fahrenheit"}"#)
            let convertResult = try await mathKit.execute(toolNamed: "convert_units", input: convertInput)
            try print("  • Conversion result: \(convertResult.toJSONString())")
        } catch {
            print("  • Math error: \(error)")
        }

        // Empty ToolKit
        let emptyKit = EmptyToolKit()
        print("  • EmptyToolKit with tools: \(emptyKit.toolNames) (count: \(emptyKit.tools.count))")
    }
}

// MARK: - Example 3: Conversation Management

extension TachikomaExamples {
    static func demonstrateConversationManagement() {
        print("Managing conversations:")

        // Create conversation
        let conversation = Conversation()
        print("  • Created empty conversation: \(conversation.messages.count) messages")

        // Add messages
        conversation.addUserMessage("Hello, how are you?")
        conversation.addAssistantMessage("I'm doing well, thank you for asking!")
        conversation.addUserMessage("What's the weather like today?")

        print("  • Added messages: \(conversation.messages.count) total")

        // Display conversation
        for (index, message) in conversation.messages.indexed() {
            let roleIcon = message.role == .user ? "👤" : "🤖"
            print("    \(index + 1). \(roleIcon) \(message.role): \(message.content)")
        }

        // Conversation operations
        let conversationCopy = conversation.copy()
        print("  • Created conversation copy: \(conversationCopy.messages.count) messages")

        conversation.clear()
        print("  • Cleared original: \(conversation.messages.count) messages")
        print("  • Copy still has: \(conversationCopy.messages.count) messages")
    }
}

// MARK: - Example 4: Usage Tracking

extension TachikomaExamples {
    static func demonstrateUsageTracking() async {
        print("Tracking AI usage and costs:")

        // Create tracker for testing
        let tracker = UsageTracker(forTesting: true)

        // Record some usage
        try? await tracker.recordUsage(
            operation: .generation,
            model: "gpt-5.5".lowercased(),
            inputTokens: 100,
            outputTokens: 50,
            cost: 0.003,
        )

        try? await tracker.recordUsage(
            operation: .analysis,
            model: "claude-opus-4".lowercased(),
            inputTokens: 200,
            outputTokens: 75,
            cost: 0.006,
        )

        try? await tracker.recordUsage(
            operation: .streaming,
            model: "grok-4".lowercased(),
            inputTokens: 150,
            outputTokens: 100,
            cost: 0.004,
        )

        // Generate reports
        let totalUsage = await tracker.getTotalUsage()
        print("  • Total operations: \(totalUsage.totalOperations)")
        print("  • Total input tokens: \(totalUsage.totalInputTokens)")
        print("  • Total output tokens: \(totalUsage.totalOutputTokens)")
        print("  • Total cost: $\(String(format: "%.6f", totalUsage.totalCost))")

        let usageReport = await tracker.generateUsageReport()
        print("  • Usage report generated with \(usageReport.sessions.count) sessions")

        // Operation types
        print("  • Available operation types:")
        for opType in OperationType.allCases {
            print("    - \(opType.displayName): \(opType.rawValue)")
        }
    }
}

// MARK: - Example 5: Error Handling

extension TachikomaExamples {
    static func demonstrateErrorHandling() {
        print("Demonstrating error handling:")

        // TachikomaError examples
        let errors: [TachikomaError] = [
            .modelNotFound("nonexistent-model"),
            .authenticationFailed("Invalid API key"),
            .apiError("Rate limit exceeded"),
            .invalidInput("Empty prompt provided"),
            .configurationError("Missing required configuration"),
        ]

        for error in errors {
            print("  • \(type(of: error)): \(error.errorDescription ?? "Unknown error")")
        }

        // AgentToolError examples
        let toolErrors: [AgentToolError] = [
            .toolNotFound("missing_tool"),
            .invalidInput("Invalid JSON format"),
            .executionFailed("Network timeout"),
            .outputFormatError("Could not serialize result"),
        ]

        for error in toolErrors {
            print("  • \(type(of: error)): \(error.errorDescription ?? "Unknown error")")
        }
    }
}

// MARK: - Example 6: Provider Factory

extension TachikomaExamples {
    static func demonstrateProviderFactory() async {
        print("Creating AI providers:")

        // Test different provider creations (these will fail without API keys, which is expected)
        let models: [(String, Model)] = [
            ("OpenAI GPT-5.5", .openai(.gpt55)),
            ("Anthropic Opus 4", .anthropic(.opus4)),
            ("Grok 4.3", .grok(.grok43)),
            ("Ollama Llama 3.3", .ollama(.llama3_3)),
        ]

        for (name, model) in models {
            do {
                let provider = try ProviderFactory.createProvider(for: model)
                print("  ✅ \(name): \(type(of: provider))")
            } catch {
                if let tachikomaError = error as? TachikomaError {
                    switch tachikomaError {
                    case let .authenticationFailed(message):
                        print("  🔑 \(name): Authentication required (\(message))")
                    default:
                        print("  ❌ \(name): \(tachikomaError.errorDescription ?? "Unknown error")")
                    }
                } else {
                    print("  ❌ \(name): \(error.localizedDescription)")
                }
            }
        }

        // Capabilities demonstration
        print("\nModel capabilities:")
        for (name, model) in models {
            print("  • \(name):")
            print("    - Vision: \(model.supportsVision)")
            print("    - Tools: \(model.supportsTools)")
            print("    - Streaming: \(model.supportsStreaming)")
        }
    }
}

// MARK: - Helper Extensions

extension String {
    static func * (lhs: String, rhs: Int) -> String {
        String(repeating: lhs, count: rhs)
    }
}

extension Model {
    var supportsVision: Bool {
        switch self {
        case .openai(.gpt55), .ollama(.llava):
            true
        default:
            false
        }
    }

    var supportsTools: Bool {
        switch self {
        case .openai, .anthropic, .grok:
            true
        case .ollama(.llama3_3):
            true
        default:
            false
        }
    }

    var supportsStreaming: Bool {
        true // Most modern models support streaming
    }
}
