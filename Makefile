PATH  := $(PATH):$(HOME)/.local/bin
SHELL := env PATH=$(PATH) /bin/bash

.PHONY: build format test lint

build:
	poetry install

format:
	poetry run ruff check . --select I --fix
	poetry run ruff format .

lint:
	poetry run ruff check . --diff
	poetry run ruff format . --check --diff

test:
	poetry run pytest tests/
