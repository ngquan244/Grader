# Teaching Assistant Grader - Documentation

## Table of Contents

1. [Getting Started](getting-started.md)
2. [Architecture](architecture.md)
3. [API Reference](api-reference.md)
4. [Adding New Tools](adding-tools.md)
5. [Configuration Guide](configuration.md)
6. [Deployment](deployment.md)
7. [Troubleshooting](troubleshooting.md)

## Quick Links

- **Installation**: See Getting Started
- **Configuration**: See Configuration Guide
- **Tool Development**: See Adding New Tools
- **API Docs**: See API Reference

## Architecture Overview

The system is built on LangGraph with a ReAct (Reasoning + Acting) pattern:

```
User Input → Agent (Reasoning) → Tool Selection → Tool Execution → Observation → Reflection → Response
```

### Key Components

- **Agent Graph**: State machine managing agent flow
- **Tools**: Modular, extensible tool system
- **UI**: Gradio-based interface
- **Config**: Centralized configuration management
- **Logger**: Comprehensive logging system

## Development Workflow

1. Make changes to `src/`
2. Add tests to `tests/`
3. Run tests: `pytest`
4. Update docs if needed
5. Commit changes

## Support

For issues or questions:
- Check [Troubleshooting](troubleshooting.md)
- Review [API Reference](api-reference.md)
- See example code in `scripts/`

---

Last updated: December 2025
