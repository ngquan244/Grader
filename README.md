---
title: Teaching Assistant Grader - LangGraph AI Agent
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 5.49.1
app_file: main.py
pinned: false
license: mit
short_description: Production-ready AI Agent for automated grading with LangGraph
---

# Teaching Assistant Grader - LangGraph ReAct Agent

Production-ready AI Agent system for automated grading and teaching assistance.


## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run setup
python scripts/setup.py

# Start application
python main.py
```

Access at: **http://127.0.0.1:7860**

##  Features

- **ReAct Pattern**: Reasoning --> Acting --> Reflection
- **Multi-step Planning**: Complex task decomposition
- **Tool Ecosystem**:Calculator, extensible
- **Error Recovery**: Automatic retry logic
- **Real-time Monitoring**: Iterations, tools, metrics


## Testing

```bash
pytest                          # Run all tests
pytest --cov=src tests/        # With coverage
python scripts/test_agent.py   # Quick test
```

##  License

MIT License

---

**Built with**: LangGraph + LangChain + Ollama + Gradio
