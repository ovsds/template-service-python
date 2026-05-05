# template-service-python

[![CI](https://github.com/ovsds/template-service-python/workflows/Check%20PR/badge.svg)](https://github.com/ovsds/template-service-python/actions?query=workflow%3A%22Check+PR%22)

Cookiecutter template for a Python service. I use it to scaffold backend services I build for myself — Poetry-based, pydantic-settings, pytest harness, and the lint/format/CI rigging I prefer.

> Personal use only — I maintain this for my own services and am not soliciting external contributions or use.

## What you get

Generated layout (Python 3.12, Poetry):

- `bin/main/` — service entrypoint package.
- `lib/app/` — app skeleton: `app.py`, `errors.py`, pydantic-settings-based `settings.py`.
- `lib/utils/` — utility modules, included selectively based on the flags below.
- `tests/{unit,integration,utils}/` — pytest harness with `pytest-asyncio` and `pytest-mock`.
- `.settings/` — dev/test config YAMLs consumed by pydantic-settings.
- `pyproject.toml` — Poetry deps + `ruff`, `black`, `pyright` (strict), `coverage`, `deptry`, `sort-all`, `toml-sort` configured.
- `Taskfile.yaml` — `init`, `lint`, `lint-fix`, `test`, `dependencies-update`, `dependencies-check`, `update-from-template`, etc. (`task --list-all` for the full surface).
- `.github/workflows/` — `Check PR` (lint + tests) and `Check PR title` (commitlint).
- `.lintstagedrc.json`, husky pre-commit, Prettier, commitlint, `.editorconfig`.

Optional, gated by cookiecutter flags answered at generation time:

- `with_docker` — `Dockerfile`, `docker-bake.hcl`, dev/test docker settings YAMLs.
- `with_trivy` — `trivy.yaml` and the CI scanning hook.
- `with_ngrok` — Taskfile entry to expose the local app via an ngrok tunnel.
- `with_aiohttp_utils` — `lib/utils/aiohttp/` helpers.
- `with_aiogram_utils` — `lib/utils/aiogram/` helpers (Telegram bot).
- `with_json_utils` — `lib/utils/json.py` (orjson wrapper).

## Quickstart

```shell
cookiecutter https://github.com/ovsds/template-service-python
```

You'll be prompted for `service_name` and the `with_*` flags above. Requires [cookiecutter](https://cookiecutter.readthedocs.io/en/stable/installation.html).

## Development

This section is for working on the template itself, not on a generated service.

### Global dependencies

- [Taskfile](https://taskfile.dev/installation/)
- [nvm](https://github.com/nvm-sh/nvm?tab=readme-ov-file#install--update-script)
- [zizmor](https://woodruffw.github.io/zizmor/installation/) — used for GHA security scanning

### Taskfile commands

For all commands see [Taskfile](Taskfile.yaml) or `task --list-all`.

## License

[MIT](LICENSE)
