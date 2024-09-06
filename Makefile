GREEN=\033[0;32m
RED=\033[0;31m
NC=\033[0m


.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: check-format
check-format: ## Run Ruff without automatic fixing.
	@echo "🐋 ${GREEN}Checking format code...${NC} 🐋"
	poetry run ruff check .

.PHONY: fix-format
fix-format: ## Run Ruff with automatic fixing (A combination of Ruff and Black)
	@echo "🐋 ${GREEN}Fixing format code...${NC} 🐋"
	poetry run ruff check --extend-select I --fix .
	poetry run ruff format .
	poetry run black .

.PHONY: test
test: ## Run the test suite
	@echo "🧪 ${GREEN}Running tests...${NC} 🧪"
	poetry run pytest
