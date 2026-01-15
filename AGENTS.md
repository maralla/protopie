# Agent Guidelines

This document contains guidelines and rules for AI agents working on this codebase.

## Type Checking Rules

### Never Ignore Type Errors

**Never** add comments like `# type: ignore` to bypass type checker issues.

Instead of ignoring type errors:

1. **Fix the underlying issue** - Understand why the type checker is complaining and address the root cause
2. **Add proper type annotations** - Ensure all functions, classes, and variables have correct type hints
4. **Use `cast()` only when necessary** - If you must use `cast()`, ensure it's truly needed and document why with a comment explaining the reasoning

### Examples

**Bad:**
```python
def foo(x: Any) -> str:
    return x.upper()  # type: ignore[attr-defined]
```

**Good:**
```python
def foo(x: str) -> str:
    return x.upper()
```

**Bad:**
```python
result = some_function()  # type: ignore
```

**Good:**
```python
result: ExpectedType = some_function()
# or fix some_function's return type annotation
```

## Code Quality Standards

### Linting

- Always run `uv run ruff check` and fix all errors
- Use `uv run ruff check --fix` for auto-fixable issues
- **Never add `# noqa` comments** to suppress linter warnings unless:
  1. The user explicitly requests it, OR
  2. You're modifying test files (where `# noqa` is acceptable for test-specific patterns)
- If complexity warnings appear (C901, PLR0912), refactor the code to reduce complexity rather than suppressing the warning
- For production code, always fix the underlying issue instead of suppressing warnings

### Type Checking

- Always run `uv run mypy` and fix all errors
- Maintain strict type checking throughout the codebase

### After Changing Python Files

**Always verify code quality after modifying Python files.**

When you modify any Python file (`.py`):

1. **Run ruff check** - `uv run ruff check <file>` to verify linting passes
2. **Run mypy check** - `uv run mypy <file>` to verify type checking passes
3. **Fix any errors** - Address all linting and type errors before considering the change complete

**Example workflow:**
```bash
# After editing protopy/ast.py
uv run ruff check protopy/ast.py
uv run mypy protopy/ast.py
```

This ensures that every change maintains code quality standards and catches issues immediately.

## File Creation Policy

### Never Create Documentation Files Unless Explicitly Requested

**Never** create markdown (.md) or documentation text files unless the user explicitly asks for them.

This includes but is not limited to:
- README files
- Documentation files
- Summary files
- Strategy files
- Implementation notes
- Test result summaries

When you want to communicate information to the user:

1. **Use your response text directly** - Provide summaries and explanations in your response
2. **Only create files if explicitly requested** - Wait for the user to ask for a file
3. **Ask if unsure** - If you think a file would be helpful, ask the user first

## Import Statement Policy

### Prefer Imports at the Top of the File

**Strongly prefer placing import statements at the top of the file.**

Import statements should be placed at the top of the file, following this order:
1. Standard library imports
2. Third-party library imports
3. Local/project imports

**Preferred:**
```python
from .errors import ParseError
from .grammar import SCALAR_TYPES

def validate(self):
    if condition:
        raise ParseError(...)
```

## General Principles

1. **Fix, don't suppress** - Always prefer fixing issues over suppressing warnings
2. **Understand before acting** - Don't blindly apply fixes; understand what the error means
3. **Maintain consistency** - Follow existing patterns and conventions in the codebase
4. **Test your changes** - Ensure type checking and linting pass after every change
5. **Ask before creating files** - Never create markdown/documentation files without explicit user request
