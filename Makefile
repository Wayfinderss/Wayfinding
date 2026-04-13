.PHONY: build up build-up down

build:
	docker compose build

up:
	docker compose down
	docker compose up -d
	@echo "Waiting for frontend to be ready..."
	@sleep 5
	open http://localhost:5173

build-up:
	docker compose down
	docker compose build
	docker compose up -d
	@echo "Waiting for frontend to be ready..."
	@sleep 5
	open http://localhost:5173

down:
	docker compose down