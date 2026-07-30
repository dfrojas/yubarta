GREEN=\033[0;32m
RED=\033[0;31m
NC=\033[0m

COMPOSE=docker compose -f docker-compose.dev.yaml
RUN_API=$(COMPOSE) run --rm api
# Lint and types need no database, so skip the api service's dependencies.
RUN_TOOL=$(COMPOSE) run --rm --no-deps api

IMAGE_NAME_LOCK_BUILDER=poetry-lock-builder

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: init
init: ## Build the image and raise the stack
	make docker-build
	make up

.PHONY: up
up: ## Raise all development containers (applies migrations first)
	COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=1 $(COMPOSE) up -d
	@echo "🐋 ${GREEN}API on http://localhost:8080 (docs at /docs)${NC} 🐋"

.PHONY: down
down: ## Stop all containers, keeping volumes
	$(COMPOSE) down

.PHONY: clean
clean: ## Stop all containers and delete their volumes (drops the dev database)
	$(COMPOSE) down -v

.PHONY: run-dev
run-dev: up ## Alias for `up`

.PHONY: logs
logs: ## Follow logs (use CONTAINER=service_name for one service)
	@if [ -z "$(CONTAINER)" ]; then \
		$(COMPOSE) logs -f; \
	else \
		$(COMPOSE) logs -f $(CONTAINER); \
	fi

.PHONY: see-logs
see-logs: logs ## Alias for `logs`

.PHONY: test
test: ## Run the test suite
	@echo "🧪 ${GREEN}Running tests...${NC} 🧪"
	$(RUN_API) pytest

.PHONY: run-tests
run-tests: test ## Alias for `test`

.PHONY: check
check: check-format run-mypy ## Run lint and type checks

.PHONY: check-format
check-format: ## Run Ruff without automatic fixing
	@echo "🐋 ${GREEN}Checking format code...${NC} 🐋"
	$(RUN_TOOL) ruff check .

.PHONY: fix-format
fix-format: ## Run Ruff with automatic fixing (linter and formatter)
	@echo "🐋 ${GREEN}Fixing format code...${NC} 🐋"
	$(RUN_TOOL) ruff format .
	$(RUN_TOOL) ruff check --fix .

.PHONY: run-mypy
run-mypy: ## Run the mypy type checker
	@echo "🐋 ${GREEN}Running mypy...${NC} 🐋"
	$(RUN_TOOL) mypy .

.PHONY: inject-alarm
inject-alarm: ## Drive the reactive path end-to-end with a fake Alertmanager alert
	@echo "🚨 ${GREEN}Injecting a fake alarm...${NC} 🚨"
	$(COMPOSE) exec api python dev/inject_alarm.py

.PHONY: incidents
incidents: ## List the most recent incidents
	$(COMPOSE) exec api python dev/inject_alarm.py --list-only

.PHONY: psql
psql: ## Open a psql shell on the dev database
	$(COMPOSE) exec postgres psql -U yubarta -d yubarta

.PHONY: shell
shell: ## Open a shell in the api container
	$(COMPOSE) exec api bash

.PHONY: migrate
migrate: ## Apply all pending database migrations (alembic upgrade head)
	# Django equivalent: python manage.py migrate
	@echo "🐋 ${GREEN}Applying migrations...${NC} 🐋"
	$(RUN_API) alembic upgrade head

.PHONY: migrate-down
migrate-down: ## Roll back the last applied migration (alembic downgrade -1)
	# Django equivalent: python manage.py migrate <app> <previous_migration> (step back one)
	@echo "🐋 ${GREEN}Rolling back last migration...${NC} 🐋"
	$(RUN_API) alembic downgrade -1

.PHONY: migration
migration: ## Autogenerate a new migration from ORM changes: make migration MSG="description"
	# Django equivalent: python manage.py makemigrations
	@if [ -z "$(MSG)" ]; then echo "${RED}MSG is required: make migration MSG=\"description\"${NC}"; exit 1; fi
	@echo "🐋 ${GREEN}Generating migration...${NC} 🐋"
	$(RUN_API) alembic revision --autogenerate -m "$(MSG)"

.PHONY: migration-check
migration-check: ## Fail if the ORM has drifted from the latest migration
	$(RUN_API) alembic check

.PHONY: docker-build
docker-build: ## Build the development image
	$(COMPOSE) build

.PHONY: update-deps
update-deps: ## Update the dependencies
	$(RUN_API) poetry update

.PHONY: generate-lock
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
