.PHONY: build up build-up down rebuild-up

build:
	docker compose build

up:
	docker compose down
	docker compose up -d
	@echo "Waiting for frontend to be ready..."
	@sleep 8
	open http://localhost:5173

build-up:
	docker compose down
	docker compose build
	docker compose up -d
	@echo "Waiting for frontend to be ready..."
	@sleep 8
	open http://localhost:5173

rebuild-up:
	docker compose down -v
	docker compose build
	REBUILD_TILES=true docker compose up -d
	@echo "Waiting for frontend to be ready..."
	@sleep 8
	open http://localhost:5173

down:
	docker compose down