# Creative AutoGPT

AI-powered creative writing system specialized for long-form novels (10万字 to 500万字).

## Features

- **Multi-LLM Intelligent Routing**: Routes different tasks to optimal LLMs
  - Qwen (Aliyun): Long context planning, outlines, character design
  - DeepSeek: Logic reasoning, evaluation, consistency checks
  - Doubao (Ark): Creative content, dialogue, prose

- **AutoGPT-Inspired Loop**: Think → Plan → Execute → Evaluate → Memory

- **Plugin System**: Extensible element management (characters, plot, world-building, foreshadowing)

- **Vector Memory**: Semantic context retrieval for long-form consistency

- **Real-time Interaction**: Preview each step and provide chat feedback

## Quick Start

### Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Copy `.env` file and configure your API keys:

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required API keys:
- `ALIYUN_API_KEY`: For Qwen (long context planning)
- `DEEPSEEK_API_KEY`: For DeepSeek (logic reasoning)
- `ARK_API_KEY`: For Doubao (creative writing)

### Initialize Database

```bash
python scripts/init_db.py init
```

### Run Server

```bash
python scripts/run_server.py
```

API will be available at http://localhost:8000

API documentation at http://localhost:8000/docs

## Project Structure

```
src/creative_autogpt/
├── core/              # Core modules (LoopEngine, TaskPlanner, Evaluator, Memory)
├── modes/             # Writing modes (Novel, Script, etc.)
├── plugins/           # Plugin system and element plugins
├── prompts/           # Prompt management and templates
├── utils/             # Utilities (LLM client, config, logger)
├── storage/           # Storage layer (session, vector, file)
└── api/               # FastAPI routes and schemas

scripts/               # Utility scripts (init_db, test_llm, run_server)
prompts/               # Prompt templates and style configs
frontend/              # React frontend (TODO)
```

## Development

### Test LLM Connectivity

```bash
python scripts/test_llm.py --test llm
```

### Run System Tests

```bash
python scripts/test_system.py
```

### Code Quality

```bash
# Format code
black src/

# Lint
pylint src/

# Type check
mypy src/
```

## Usage

### Create a Session

```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "title": "我的玄幻小说",
    "mode": "novel",
    "goal": {
      "genre": "玄幻",
      "theme": "成长与复仇",
      "style": "热血",
      "length": "100万字"
    },
    "config": {
      "chapter_count": 10
    }
  }'
```

### Start Execution (WebSocket)

Connect to `ws://localhost:8000/ws/ws` and send:

```json
{
  "event": "subscribe",
  "session_id": "<session_id>"
}

{
  "event": "start",
  "session_id": "<session_id>"
}
```

## Documentation

- [Architecture](ARCHITECTURE.md) - Complete architecture documentation
- [docs/](docs/) - Additional documentation

## License

MIT License
