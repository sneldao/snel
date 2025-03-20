# Makefile for Dowse Pointless

.PHONY: help run dev test install clean deploy format venv reset-venv

help:
	@echo "Available commands:"
	@echo "  make run         - Run the server in production mode"
	@echo "  make dev         - Run the server in development mode with hot reload"
	@echo "  make test        - Run tests"
	@echo "  make install     - Install dependencies"
	@echo "  make clean       - Clean up cache and log files"
	@echo "  make deploy      - Deploy to Vercel"
	@echo "  make format      - Format code"
	@echo "  make venv        - Create a new virtual environment"
	@echo "  make reset-venv  - Delete and recreate the virtual environment"

run:
	python server.py

dev:
	PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

test:
	pytest

install:
	pip install -r requirements.txt

venv:
	python -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

reset-venv:
	rm -rf .venv
	python -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip
	. .venv/bin/activate && pip install -r requirements.txt

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type f -name "coverage.xml" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	rm -f app.log info.log

deploy:
	./deploy.sh

format:
	black . --verbose -l 100
	isort . --profile black
	python -m flake8 --ignore=E501,E203,W503

lint:
	python -m flake8 --ignore=E501,E203,W503 