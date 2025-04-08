GREEN=\033[0;32m
RED=\033[0;31m
NC=\033[0m

IMAGE_NAME_LOCK_BUILDER=poetry-lock-builder

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: check-format
check-format: ## Run Ruff without automatic fixing.
	@echo "🐋 ${GREEN}Checking format code...${NC} 🐋"
	poetry run ruff check .

.PHONY: fix-format
fix-format: ## Run Ruff with automatic fixing (linter and automatic formatter)
	@echo "🐋 ${GREEN}Fixing format code...${NC} 🐋"
	poetry run ruff format .
	poetry run ruff check --fix .

.PHONY: test
test: ## Run the test suite
	@echo "🧪 ${GREEN}Running tests...${NC} 🧪"
	poetry run pytest

build-image: ## Build the development image
	COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=1 docker compose -f docker-compose.dev.yaml build --no-cache

run-dev: ## Run all development containers
	COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=1 docker compose -f docker-compose.dev.yaml up -d

generate-lock:  ## Regenerate the lock file and copy it from the container to the local environment.
	@echo "🚧 Building Docker image..."
	@docker build -t $(IMAGE_NAME_LOCK_BUILDER) .
	@echo "📦 Creating temporary container..."
	@CONTAINER_ID=$$(docker create $(IMAGE_NAME_LOCK_BUILDER)) && \
	echo "📤 Copying poetry.lock to host..." && \
	docker cp $$CONTAINER_ID:/app/poetry.lock poetry.lock && \
	echo "🧹 Cleaning up container and image..." && \
	docker rm -f $$CONTAINER_ID > /dev/null && \
	docker rmi -f $(IMAGE_NAME_LOCK_BUILDER) > /dev/null && \
	echo "✅ Done. poetry.lock updated."
