# Nagisa ChatAgent - Agentic Instructions & Guidelines

Welcome, autonomous agent! This document (`AGENTS.md`) acts as the central source of truth for repository structure, style guidelines, and execution commands. Read this thoroughly before operating in the `Nagisa/ChatAgent` repository.

## 1. Project Overview & Architecture

This repository contains a Python-based role-playing AI Chat Agent (Nagisa). It integrates `mem0ai` for long-term memory management and `openai` (or compatible API wrappers) for Large Language Model interactions.

### 1.1 Core Modules
- `main.py`: The entry point for the CLI application. Handles environment checking, user I/O, and graceful exits.
- `agent.py`: `RolePlayingAgent` class managing the chat context (sliding window short-term memory), prompt building, and interaction flow.
- `memory_manager.py`: `MemoryManager` class interfacing with `mem0` and local ChromaDB for long-term vector-based memory.
- `llm_client.py`: `LLMClient` wrapping the OpenAI API client to keep business logic agnostic of the specific LLM implementation.
- `config.py`: Centralized configuration management using `python-dotenv` and predefined settings for `mem0`.

---

## 2. Build, Lint, and Test Commands

The project is a lightweight Python CLI application. No complex compilation is required, but strict adherence to code quality tools is expected.

### 2.1 Setup & Execution
```bash
# Setup virtual environment and install dependencies
python -m venv venv
# Windows:
venv\Scripts\activate
# Unix:
source venv/bin/activate

pip install -r requirements.txt

# Run the application
python main.py
```

### 2.2 Linting & Formatting
If instructed to format code or fix linting issues, prefer `ruff` as the primary tool.
```bash
# Check for linting errors across the codebase
ruff check .

# Fix auto-fixable linting errors safely
ruff check --fix .

# Format code consistently
ruff format .
```

### 2.3 Testing (using `pytest`)
While the repository may not currently have extensive test coverage, any new tests must use `pytest`. Always place test files in a top-level `tests/` directory.

```bash
# Run the entire test suite
pytest tests/

# Run a specific test file
pytest tests/test_agent.py

# Run a single specific test function with verbose output
pytest tests/test_agent.py::test_process_message -v

# Run tests with print output enabled (useful for debugging)
pytest -s tests/
```

---

## 3. Code Style & Engineering Guidelines

When writing, refactoring, or modifying code in this repository, strictly adhere to the following rules to maintain idiomatic consistency.

### 3.1 Imports
- Group imports sequentially: standard library -> third-party packages -> local project modules.
- Use absolute imports for local modules (e.g., `from memory_manager import MemoryManager`).
- Avoid wildcard imports (`from module import *`) at all costs to prevent namespace pollution.

### 3.2 Formatting & Syntax
- Use 4 spaces for indentation. No tabs.
- Limit line length to 100-120 characters to maintain readability.
- Use f-strings for string interpolation instead of `.format()` or `%`.
- Be mindful of cross-platform execution. Note the Windows UTF-8 console fix in `main.py` (`sys.stdout.reconfigure(encoding='utf-8')`). Maintain this compatibility mindset.

### 3.3 Type Hinting
- **Strict Typing**: Always use Python type hints for function arguments and return values. This is crucial for maintainability.
  *Good*: `def get_relevant_memories(self, query: str, limit: int = 3) -> str:`
  *Bad*: `def get_relevant_memories(self, query, limit=3):`
- For complex data structures, utilize the `typing` module (e.g., `from typing import List, Dict, Optional, Any`).

### 3.4 Naming Conventions
- **Classes**: `PascalCase` (e.g., `RolePlayingAgent`, `MemoryManager`).
- **Functions & Methods**: `snake_case` (e.g., `process_message`, `get_relevant_memories`).
- **Variables**: `snake_case` (e.g., `user_message`, `chat_history`).
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `LLM_API_KEY`, `MEMORY_DB_PATH`).
- **Private Members**: Prefix internal methods or variables with a single underscore (e.g., `_build_system_prompt`).

### 3.5 Documentation & Comments
- **Language**: The primary language for documentation and code comments in this repository is **Chinese**. When writing new logic or updating docstrings, write them in Chinese to match the existing codebase context.
- Provide clear module-level and class-level docstrings explaining their core responsibility.
- Use inline comments only to explain *why* complex or non-obvious logic is implemented a certain way, rather than *what* it does.

### 3.6 Error Handling & Logging
- **Logging vs. Printing**: Use the built-in `logging` module (`logging.info`, `logging.error`) for internal system messages and debugging. Reserve `print` strictly for user-facing outputs in the CLI interface (primarily within `main.py`).
- **Exception Catching**: Always catch specific exceptions where possible. If catching a generic `Exception`, log it comprehensively with the error details.
  ```python
  try:
      self.memory.add(interaction, user_id=self.user_id)
  except Exception as e:
      logging.error(f"Failed to add memory interaction: {e}")
  ```
- **Graceful Degradation**: Ensure the application degrades gracefully on failure. For example, `LLMClient` returns an error string prefixed with `❌` instead of crashing the entire application.

### 3.7 State Management & Memory
- Do not use global state variables. Encapsulate state within class instances (e.g., the `chat_history` list in the `RolePlayingAgent` instance).
- Short-term memory (context sliding window) must strictly respect the `history_limit` configuration to avoid exceeding LLM context windows.
- Long-term memory logic relies entirely on `mem0ai`. Ensure string formatting for interactions remains consistent before storage.

---

## 4. Autonomous Agent Directives (Cursor / Copilot / Tool-Calling Agents)

*(Note: There were no existing `.cursorrules` or `.github/copilot-instructions.md` files in the repository, so these act as the definitive rules.)*

1. **Information Gathering**: Do not assume file locations. Use search tools (`glob`, `grep`) to locate configurations and logic before editing.
2. **Absolute Paths**: When using filesystem tools (e.g., file reads/writes), always construct full absolute paths (e.g., `D:\python_code\projects\Nagisa\ChatAgent\agent.py`).
3. **Dependency Management**: Never introduce new third-party dependencies into `requirements.txt` unless explicitly requested by the user. Rely on the standard library when possible.
4. **Environment Safety**: Never hardcode API keys, tokens, or credentials in any file. Always route them through `config.py` which extracts from the environment or `.env` file.
5. **No Hallucinated Tests**: Verify the existence of tests using filesystem tools before attempting to run them. If tests do not exist, ask the user if they want them generated.