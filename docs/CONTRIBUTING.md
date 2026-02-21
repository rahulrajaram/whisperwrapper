# Contributing to Whisper GUI

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the Whisper GUI project.

## Code of Conduct

Be respectful, inclusive, and constructive. All contributors are expected to follow professional standards and treat each other with respect.

## Getting Started

### Prerequisites

- Git
- Python 3.8+
- Basic knowledge of Python and PyQt6 (helpful but not required)

### Setting Up Your Development Environment

1. **Fork the repository** on GitHub

2. **Clone your fork locally**:
   ```bash
   git clone https://github.com/YOUR-USERNAME/whisper-gui.git
   cd whisper-gui
   ```

3. **Add upstream remote** (to stay in sync):
   ```bash
   git remote add upstream https://github.com/rahulrajaram/whisper-gui.git
   git remote -v  # Verify both origin and upstream are present
   ```

4. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

5. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

6. **Verify installation**:
   ```bash
   pytest --version
   black --version
   flake8 --version
   ```

## Development Workflow

### 1. Create a Feature Branch

Always create a new branch for your work:

```bash
git checkout -b feature/my-feature-name
```

Branch naming conventions:
- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `refactor/description` - Code refactoring
- `docs/description` - Documentation updates
- `test/description` - Test additions

### 2. Make Your Changes

- Keep changes focused and atomic (one feature per branch)
- Write clear, descriptive commit messages
- Update docstrings and comments as you go
- Add tests for new functionality

### 3. Run Tests and Linters

Before committing, ensure your code passes all checks:

```bash
# Run tests with coverage
pytest --cov=whisper_app

# Format code
black src/ tests/

# Check code style
flake8 src/ tests/

# Type checking
mypy src/

# Import sorting
isort src/ tests/
```

### 4. Commit Your Changes

```bash
git add <files>
git commit -m "Type: Brief description

Detailed explanation of the change if needed.
- Bullet points for complex changes
- References to related issues #123
"
```

Commit message format:
- First line: `Type: Brief description (max 50 chars)`
- Blank line
- Body: Detailed explanation (wrap at 72 chars)
- References: `Fixes #123` or `Related to #456`

### 5. Push and Create Pull Request

```bash
git push origin feature/my-feature-name
```

Then create a Pull Request on GitHub with:
- Clear title describing the change
- Description explaining what and why
- Reference to related issues
- Screenshots for UI changes

## Code Style Guidelines

### Python Style

Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with these tools:

```bash
# Format code (enforced)
black src/ tests/

# Line length: 100 characters (see pyproject.toml)
# Use 4 spaces for indentation
# Class names: PascalCase
# Function/variable names: snake_case
# Constants: UPPER_SNAKE_CASE
```

### Docstrings

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """Brief description of what the function does.

    Longer description if needed, explaining the purpose
    and behavior of the function.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When input validation fails
        RuntimeError: When operation fails

    Example:
        >>> result = function_name("test", 42)
        >>> print(result)
        True
    """
    pass
```

### Type Hints

Include type hints for all function signatures:

```python
from typing import List, Optional, Dict

def process_audio(audio_data: List[bytes], config: Dict[str, int]) -> str:
    """Process audio data and return transcription."""
    pass

class RecordingWorker(QObject):
    """Worker for recording tasks."""

    def __init__(self, device_index: Optional[int] = None) -> None:
        """Initialize the worker."""
        pass
```

### Comments

- Use comments for WHY, not WHAT
- Keep comments up-to-date with code
- Use clear, concise language

```python
# Good - explains reasoning
if timeout > MAX_TIMEOUT:
    # Prevent resource exhaustion from very long recordings
    timeout = MAX_TIMEOUT

# Avoid - obvious from code
x = x + 1  # Increment x
```

## Testing

### Writing Tests

Tests go in `tests/` directory with naming convention `test_*.py`:

```python
# tests/test_cli.py
import pytest
from whisper_app.cli import WhisperCLI

class TestWhisperCLI:
    """Test WhisperCLI functionality."""

    @pytest.fixture
    def cli(self):
        """Create a test CLI instance."""
        return WhisperCLI(headless=True, debug=True)

    def test_initialization(self, cli):
        """Test that WhisperCLI initializes correctly."""
        assert cli.model is not None
        assert cli.recording is False

    def test_microphone_selection(self, cli):
        """Test microphone can be selected."""
        # Implementation
        pass

    @pytest.mark.skip(reason="Requires real audio device")
    def test_real_audio_recording(self):
        """Test with real audio input."""
        pass
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_cli.py

# Run specific test
pytest tests/test_cli.py::TestWhisperCLI::test_initialization

# Run with coverage
pytest --cov=whisper_app --cov-report=html

# Run only fast tests (mark slow with @pytest.mark.slow)
pytest -m "not slow"
```

### Test Coverage

Aim for >80% code coverage on new code:

```bash
pytest --cov=whisper_app --cov-report=term-missing
```

## Documentation

### Updating Documentation

- Update relevant `.md` files in `docs/` directory
- Keep README.md in sync with changes
- Use clear headings and formatting
- Include code examples where helpful

### Adding New Features

If adding a new feature:
1. Update relevant documentation
2. Add docstrings explaining the feature
3. Include usage examples in docstrings
4. Consider adding a section to README.md

## Submitting Changes

### Pull Request Checklist

Before submitting:
- [ ] Fork is synced with upstream (`git fetch upstream && git rebase upstream/master`)
- [ ] Branch created from latest master
- [ ] Changes are atomic and focused
- [ ] All tests pass (`pytest`)
- [ ] Code formatted (`black src/ tests/`)
- [ ] No style issues (`flake8 src/ tests/`)
- [ ] Type checking passes (`mypy src/`)
- [ ] Docstrings added/updated
- [ ] Commit messages are clear
- [ ] Related issues referenced in PR description

### Pull Request Description Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Code refactoring

## Related Issues
Fixes #123
Related to #456

## Changes Made
- Detailed change 1
- Detailed change 2
- Detailed change 3

## Testing
How was this tested?
- [ ] New test added
- [ ] Existing tests updated
- [ ] Manual testing done

## Screenshots (if UI changes)
Add screenshots showing the change.

## Additional Context
Any additional information needed to understand the change.
```

## Common Tasks

### Adding a New Module

```bash
# Create module in src/whisper_app/
touch src/whisper_app/new_module.py

# Add to __init__.py if it's a public API
# tests/test_new_module.py for tests
```

### Fixing a Bug

1. Create issue if not already reported
2. Create branch: `git checkout -b bugfix/issue-description`
3. Add test that demonstrates the bug
4. Fix the bug
5. Verify test passes
6. Document the fix in commit message

### Refactoring Code

- Ensure refactoring preserves functionality
- All tests must pass after refactoring
- Large refactors should be broken into smaller PRs
- Mention performance improvements if any

## Performance Considerations

- Profile code before optimizing: `python -m cProfile`
- Test with realistic data sizes
- Consider impact on systems with limited resources
- Document performance tradeoffs

## Security Considerations

- Never commit credentials or API keys
- Use environment variables for sensitive config
- Validate all user input
- Review dependencies for known vulnerabilities
- Follow PyQt security best practices

## Review Process

### What Happens After You Submit a PR

1. **Automated checks**: CI/CD pipeline runs tests
2. **Code review**: Maintainers review code and style
3. **Feedback**: Comments on specific changes
4. **Revisions**: Address feedback and update
5. **Approval**: PR is approved
6. **Merge**: Changes merged to master

### Responding to Feedback

- Address all comments respectfully
- Ask for clarification if unclear
- Update code based on feedback
- Request re-review after updates

## Release Process

Releases follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

Released by maintainers, but all contributions are appreciated!

## Getting Help

- **Documentation**: See `docs/` directory
- **Issues**: Search existing issues first
- **Discussions**: Use GitHub Discussions
- **Email**: rahulrajaram2005@gmail.com

## Recognition

Contributors are recognized in:
- GitHub contributors page
- Release notes
- Project documentation

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Whisper GUI! 🎉
