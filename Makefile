# Makefile for Dowse Pointless

.PHONY: help dev all-dev backend-dev frontend-dev telegram-dev install clean docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make backend-dev   - Run the backend server in development mode"
	@echo "  make frontend-dev  - Run the frontend in development mode"
	@echo "  make telegram-dev  - Run the telegram bot in development mode"
	@echo "  make dev           - Start both backend and frontend concurrently"
	@echo "  make all-dev       - Start backend, frontend, and telegram bot concurrently"
	@echo "  make install       - Install dependencies for all components"
	@echo "  make clean         - Clean up cache and temporary files"
	@echo "  make docker-up     - Start all services with Docker"
	@echo "  make docker-down   - Stop all Docker services"

# Backend commands
backend-dev:
	cd backend && \
	python -m venv .venv && \
	. .venv/bin/activate && \
	pip install -r requirements.txt && \
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

# Frontend commands
frontend-dev:
	cd frontend && \
	npm install && \
	npm run dev

# Development: start both backend & frontend
dev:
	@echo "Starting backend and frontend..."
	npx concurrently --names "BACKEND,FRONTEND" --prefix-colors "blue.bold,green.bold" --kill-others "make backend-dev" "make frontend-dev"

# Development: start backend, frontend, and telegram bot
all-dev:
	@echo "Starting backend, frontend, and telegram bot..."
	npx concurrently --names "BACKEND,FRONTEND,TELEGRAM" --prefix-colors "blue.bold,green.bold,yellow.bold" --kill-others "make backend-dev" "make frontend-dev" "make telegram-dev"

# Telegram bot commands
telegram-dev:
	cd telegram-bot && \
	python -m venv .venv && \
	. .venv/bin/activate && \
	pip install -r requirements.txt && \
	python bot.py

# Install dependencies for all components
install:
	# Backend
	cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
	# Frontend
	cd frontend && npm install
	# Telegram bot
	cd telegram-bot && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

# Clean up
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
	find . -type d -name "node_modules" -exec rm -rf {} +
	find . -type d -name ".next" -exec rm -rf {} +

# Docker commands
docker-up:
	docker-compose up --build -d

docker-down:
	docker-compose down
	./deploy.sh

format:
	black . --verbose -l 100
	isort . --profile black
	python -m flake8 --ignore=E501,E203,W503

lint:
	python -m flake8 --ignore=E501,E203,W503