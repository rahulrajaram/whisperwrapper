.PHONY: help install install-dev test test-cov clean format lint type-check run systemd-reload

help:
	@echo "Available commands:"
	@echo "  make install        - Install package in production mode"
	@echo "  make install-dev    - Install package in development mode with dev dependencies"
	@echo "  make test           - Run all tests"
	@echo "  make test-cov       - Run tests with coverage report"
	@echo "  make clean          - Clean build artifacts and cache"
	@echo "  make format         - Format code with black and isort"
	@echo "  make lint           - Run flake8 linter"
	@echo "  make type-check     - Run mypy type checker"
	@echo "  make run            - Run the GUI application"
	@echo "  make systemd-reload - Reload and restart systemd service"

install:
	pip install .

install-dev:
	pip install -e ".[dev]"

test:
	pytest tests/

test-cov:
	pytest --cov=whisper_app --cov-report=html --cov-report=term tests/
	@echo "Coverage report generated in htmlcov/index.html"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

format:
	black src/ tests/
	isort src/ tests/

lint:
	flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503

type-check:
	mypy src/whisper_app/ --ignore-missing-imports

run:
	python -m whisper_app

systemd-reload:
	systemctl --user daemon-reload
	systemctl --user restart whisper-gui.service
	systemctl --user status whisper-gui.service
