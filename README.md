# template-service-python

[![CI](https://github.com/ovsds/template-service-python/workflows/Check%20PR/badge.svg)](https://github.com/ovsds/template-service-python/actions?query=workflow%3A%22Check+PR%22)

Cookiecutter template for a Python service. I use it to scaffold backend services I build for myself — Poetry-based, pydantic-settings, pytest harness, and the lint/format/CI rigging I prefer.

> Personal use only — I maintain this for my own services and am not soliciting external contributions or use.

## What you get

Generated layout (Poetry; Python 3.15, or 3.14 with `with_aiogram_utils`, as aiogram supports Python <3.15 only):

- `bin/main/` — service entrypoint package.
- `lib/app/` — app skeleton: `app.py`, `errors.py`, pydantic-settings-based `settings.py`.
- `lib/utils/` — utility modules, included selectively based on the flags below.
- `tests/{unit,integration,utils}/` — pytest harness with `pytest-asyncio` and `pytest-mock`.
- `.settings/` — dev/test config YAMLs consumed by pydantic-settings.
- `pyproject.toml` — Poetry deps + `ruff`, `black`, `pyright` (strict), `coverage`, `deptry`, `sort-all`, `toml-sort` configured.
- `mise.toml` and `mise-tasks/` — a [mise monorepo config root](https://mise.jdx.dev/tasks/monorepo.html) with `init`, `lint`, `lint-fix`, `test`, `clean`, `dependencies-update`, `dependencies-check`, `update-from-template`, etc. (`mise tasks ls` for the full surface).
- `.github/workflows/` — `Check PR` (lint + tests) and `Check PR title` (commitlint).
- `.lintstagedrc.json`, husky pre-commit, Prettier, commitlint, `.editorconfig`.

Optional, gated by cookiecutter flags answered at generation time:

- `with_docker` — `Dockerfile`, `docker-bake.hcl`, dev/test docker settings YAMLs.
- `with_trivy` — `trivy.yaml` and the CI scanning hook.
- `with_ngrok` — mise task to expose the local app via an ngrok tunnel.
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

- [mise](https://mise.jdx.dev/installing-mise.html), activated in the shell (`eval "$(mise activate zsh)"`)

All other tools are pinned in [mise.toml](mise.toml).

### mise tasks

For all commands see [mise.toml](mise.toml) or `mise tasks ls`.

## License

[MIT](LICENSE)
