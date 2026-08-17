# AI CLI

A command-line interface for querying AI models through the Tachikoma library.

## Building

```bash
# Clone and build
git clone https://github.com/steipete/tachikoma.git
cd tachikoma
swift build --product ai-cli

# Install globally (optional)
swift build -c release --product ai-cli
cp .build/release/ai-cli /usr/local/bin/ai-cli
```

## Usage

```bash
# Basic usage
ai-cli "What is the capital of France?"

# Specify a model
ai-cli --model claude "Explain quantum computing"

# Stream the response
ai-cli --stream --model gpt-5.5 "Write a short story"
```

## Parameters

| Option | Description |
|--------|-------------|
| `-m, --model <MODEL>` | Specify the AI model to use |
| `--api <chat\|responses>` | For OpenAI models: select API type (default: responses for GPT-5) |
| `-s, --stream` | Stream the response in real-time |
| `--thinking` | Show GPT-5 reasoning process (note: API currently doesn't expose actual reasoning) |
| `--verbose, -v` | Show detailed debug output |
| `--config` | Show current configuration and API key status |
| `--help, -h` | Show help message |
| `--version` | Show version information |

## Environment Variables

Set API keys for your providers:

```bash
export OPENAI_API_KEY='sk-...'         # OpenAI models
export ANTHROPIC_API_KEY='sk-ant-...'  # Claude models
export GEMINI_API_KEY='...'            # Gemini models (legacy GOOGLE_API_KEY also accepted)
export MISTRAL_API_KEY='...'           # Mistral models
export GROQ_API_KEY='gsk-...'          # Groq models
export X_AI_API_KEY='xai-...'          # Grok models
# Ollama runs locally, no API key needed
```

Add to your shell profile (`~/.zshrc`, `~/.bashrc`) for persistence.

## Supported Models

### OpenAI
- **GPT-5 Series**: `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.4-nano`, `gpt-5`, `gpt-5-mini`, `gpt-5-nano`

### Anthropic
- **Claude 4.x**: `claude-opus-4-7`, `claude-opus-4-5`, `claude-opus-4-1-20250805`, `claude-sonnet-4-6`, `claude-sonnet-4-5-20250929`, `claude-haiku-4-5`

### Google
- **Gemini**: `gemini-3.1-pro-preview`, `gemini-3.1-flash-lite`, `gemini-3-flash-preview`, `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`

### Others
- **Mistral**: `mistral-large-latest`, `mistral-medium-latest`, `mistral-medium-3-5`, `mistral-small-latest`, `open-mistral-nemo-2407`, `codestral-latest`
- **Groq**: `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`
- **Grok**: `grok-4.3`, `grok-4.20-0309-reasoning`, `grok-4.20-0309-non-reasoning`
- **Ollama** (local): `llama3.3`, `llava`, any installed model

### Model Shortcuts
- `claude` → claude-opus-4-7
- `gpt` → gpt-5.5
- `gemini` → gemini-3.1-pro-preview
- `grok` → grok-4.3
- `llama` → llama3.3

## Examples

```bash
# Quick queries
ai-cli "What is 2+2?"
ai-cli --model claude "Write a haiku about coding"

# Streaming
ai-cli --stream --model gpt-5 "Explain the theory of relativity"

# API selection for OpenAI
ai-cli --model gpt-5 --api chat "Use Chat Completions API"
ai-cli --model gpt-5.5 --api responses "Use Responses API"

# Debug mode
ai-cli --verbose --model opus "Debug this request"

# Check configuration
ai-cli --config
```

## License

MIT License - See [LICENSE](../../LICENSE) file for details.
