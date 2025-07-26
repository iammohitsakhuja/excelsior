# Copilot Instructions for Excelsior

## Project Description
Excelsior is a CLI application for working with Excel and CSV files. The application follows a command-based structure:
```
excelsior <command> [options]
```

Each command is associated with a script that performs specific operations on Excel/CSV files, such as conversion, merging, extraction, transformation, analysis, and report generation. (Not all features have been implemented yet!)


## General Guidelines
- Prefer functional, testable, and modular code
- Use `argparse` for CLI argument parsing with comprehensive help text
- Use type hints for all function parameters and return values
- Use `@dataclass` for structured data models
- Write meaningful docstrings and inline comments, following Google/NumPy style
- Include logging using the centralized logger utility (`excelsior.utils.logger`)
- Handle errors gracefully with user-friendly error messages
- Use `make` commands for all development tasks (formatting, linting, testing)
- Leverage VS Code tasks for integrated development workflow
- **Do not include full project structure** in documentation or instructions as it's evolving
- **Do not generate redundant documentation files or summary files**, unless explicitly asked for.

## Code Style & Quality
- Use `ruff` for formatting, linting, and import sorting with configuration in `pyproject.toml`
- Use `uv` for dependency management and Python environment handling
- Use type hints and consider `mypy` for static analysis
- Include docstrings for all public functions and classes
- Use specific exception types and provide context

## Excel/CSV Processing Guidelines
- Use `pandas` for primary data manipulation and transformation operations
- Use `openpyxl` for Excel-specific features not supported by pandas
- Handle large files efficiently with chunked processing when appropriate
- Support both absolute and relative file paths in all commands
- Validate input files exist and have correct format before processing
- Implement error handling for common Excel/CSV issues (formatting problems, missing columns)
- Provide clear progress feedback for long-running operations

## Command Structure
- Each command should be implemented as a separate module
- Commands should follow a consistent interface pattern
- Implement comprehensive help text for each command and option
- Include examples in help text for common use cases
- Support both verbose and short-form options where appropriate
- Validate command inputs before performing operations

## Testing
- Write tests for all core functionality
- Use `pytest` for writing and running tests
- Include test fixtures with sample Excel/CSV files
- Test edge cases (empty files, malformed data, large files)
- Mock external dependencies for unit tests
- Implement integration tests for complete command workflows
