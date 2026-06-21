.PHONY: help backend frontend dev seed test build docker compose-up

help:
	@echo "Targets:"
	@echo "  backend     - run FastAPI (mock auth, synthetic data) on :8000"
	@echo "  frontend    - run Vite dev server on :5173 (proxies /api to :8000)"
	@echo "  seed        - (re)seed folders + demo content"
	@echo "  test        - run backend tests"
	@echo "  build       - build the SPA into backend/static"
	@echo "  docker      - build the single-container image"
	@echo "  compose-up  - run the full stack (portal + postgres) via compose"

backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

seed:
	cd backend && . .venv/bin/activate && python -m app.seed

test:
	cd backend && . .venv/bin/activate && pytest -q

build:
	cd frontend && npm install && npm run build

docker:
	docker build -f deploy/docker/Dockerfile -t bi-portal:local .

compose-up:
	docker compose -f deploy/docker/docker-compose.yml up --build
