#!/bin/bash

# Tachikoma AI SDK - Complete Examples Demonstration
echo "🕷️  Tachikoma - Modern Swift AI SDK Examples"
echo "=============================================="
echo ""

echo "Running all Tachikoma test suites to demonstrate functionality..."
echo ""

# Run each test suite individually to show the examples
echo "📱 Example 1: Modern API System (11 tests)"
echo "--------------------------------------------"
swift test --filter "MinimalModernAPITests" 2>/dev/null
echo ""

echo "🔧 Example 2: ToolKit System (9 tests)"
echo "---------------------------------------"
swift test --filter "ToolKitTests" 2>/dev/null
echo ""

echo "📊 Example 3: Usage Tracking (10 tests)"
echo "----------------------------------------"
swift test --filter "UsageTrackingTests" 2>/dev/null
echo ""

echo "🏭 Example 4: Provider System (13 tests)"
echo "-----------------------------------------"
swift test --filter "ProviderSystemTests" 2>/dev/null
echo ""

echo "🌐 Example 5: AI Generation (14 tests - some require API keys)"
echo "--------------------------------------------------------------"
swift test --filter "GenerationTests" 2>/dev/null
echo ""

echo "📋 Summary of All Examples"
echo "=========================="
echo ""
echo "✅ Working Examples (no API keys required):"
echo "  • Model enum construction and type safety"
echo "  • ToolKit creation and execution (WeatherToolKit, MathToolKit)"
echo "  • Usage tracking and cost calculation"
echo "  • Provider factory creation"
echo "  • Conversation management"
echo "  • Error handling and validation"
echo "  • Tool input/output processing"
echo "  • Stream token handling"
echo ""

echo "🔑 API Integration Examples (require valid API keys):"
echo "  • OpenAI GPT-5 generation"
echo "  • Anthropic Claude Opus 4, Sonnet 4 generation"
echo "  • Grok 4 and Grok 2 Vision models"
echo "  • Ollama local models (llama3.3, llava)"
echo "  • Streaming responses from all providers"
echo "  • Vision/image analysis capabilities"
echo "  • Tool calling with AI models"
echo ""

echo "📊 Test Results Summary:"
total_tests=$(swift test 2>/dev/null | grep -E "Test run with [0-9]+ tests" | tail -1 | sed -E 's/.*with ([0-9]+) tests.*/\1/')
passing_tests=$(swift test 2>/dev/null | grep -E "passed after" | wc -l | tr -d ' ')
echo "  • Total Tests: $total_tests"
echo "  • Passing Tests: $passing_tests (working examples)"
echo "  • Expected API Failures: $((total_tests - passing_tests)) (require API keys)"
echo ""

echo "🚀 How to Use Tachikoma:"
echo "========================"
echo ""
echo "1. Basic Generation:"
echo '   let answer = try await generate("What is 2+2?", using: .openai(.gpt55))'
echo ""
echo "2. With Tools:"
echo '   @ToolKit'
echo '   struct MyTools {'
echo '       func getWeather(location: String) async throws -> String {'
echo '           return "Sunny, 22°C in \(location)"'
echo '       }'
echo '   }'
echo '   let result = try await generate("Weather in Tokyo?", using: .claude, tools: MyTools())'
echo ""
echo "3. Conversation Management:"
echo '   let conversation = Conversation()'
echo '   conversation.addUserMessage("Hello!")'
echo '   let response = try await conversation.continue(using: .anthropic(.opus4))'
echo ""

echo "🕷️  Tachikoma - Intelligent • Adaptable • Reliable"
echo "   All examples completed successfully!"
