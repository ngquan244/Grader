# Tests for Teaching Assistant Grader

## Running Tests

```bash
# Install pytest
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/
```

## Test Structure
- `test_agent.py` - Agent functionality tests
- `test_tools.py` - Tool execution tests
- `test_ui.py` - UI component tests
