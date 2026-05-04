.PHONY: help install dev seed run api dashboard test lint format clean docker

help:
	@echo "AgroSmart AI - Comenzi disponibile:"
	@echo "  make install   - Instaleaza dependentele de productie"
	@echo "  make dev       - Instaleaza dependentele de dezvoltare"
	@echo "  make seed      - Populeaza DB cu date demo"
	@echo "  make run       - Porneste API + Dashboard"
	@echo "  make api       - Porneste doar FastAPI"
	@echo "  make dashboard - Porneste doar Gradio"
	@echo "  make test      - Ruleaza testele"
	@echo "  make lint      - Verifica codul cu ruff"
	@echo "  make format    - Formateaza codul cu black + ruff"
	@echo "  make clean     - Sterge cache-urile"
	@echo "  make docker    - Build + run Docker Compose"

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements-dev.txt

seed:
	python -m scripts.seed

run:
	python run.py

api:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dashboard:
	python -m dashboard.app

test:
	pytest --cov=app --cov-report=term-missing

lint:
	ruff check app tests scripts dashboard

format:
	ruff check --fix app tests scripts dashboard
	black app tests scripts dashboard

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage

docker:
	docker-compose up --build
