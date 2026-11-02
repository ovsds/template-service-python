#!/usr/bin/env python
import pathlib
import shutil


def remove_folder(folder_path: str, missing_ok: bool = False) -> None:
    folder = pathlib.Path(folder_path)
    if missing_ok and not folder.exists():
        return
    shutil.rmtree(folder)


def remove_file(file_path: str, missing_ok: bool = True) -> None:
    file = pathlib.Path(file_path)
    file.unlink(missing_ok=missing_ok)


if __name__ == "__main__":
    if "{{ cookiecutter.with_trivy }}" != "true":
        remove_file("trivy.yaml")

    if "{{ cookiecutter.with_docker }}" != "true":
        remove_file(".settings/dev_docker.yaml")
        remove_file(".settings/test_docker.yaml")

    if "{{ cookiecutter.with_aiogram_utils }}" != "true":
        remove_folder("lib/utils/aiogram")

    if "{{ cookiecutter.with_prometheus }}" != "true":
        remove_file("lib/utils/aiohttp/metrics.py")
        remove_file("tests/unit/utils/aiohttp/test_metrics.py")

    if "{{ cookiecutter.__with_http_server }}" != "true":
        remove_file("lib/app/http_server.py")
        remove_file("lib/utils/aiohttp/app.py")
        remove_file("lib/utils/aiohttp/error_handling.py")
        remove_file("lib/utils/aiohttp/handlers/app_info.py")
        remove_file("lib/utils/aiohttp/handlers/base.py")
        remove_file("lib/utils/aiohttp/lifecycle.py")
        remove_file("lib/utils/aiohttp/openapi.py")
        remove_folder("tests/unit/app")
        remove_folder("tests/unit/utils/aiohttp")

    if "{{ cookiecutter.__with_aiohttp }}" != "true":
        remove_folder("lib/utils/aiohttp")

    # lib/utils/aiohttp/handlers/responses.py imports lib.utils.json
    if "{{ cookiecutter.__with_json }}" != "true":
        remove_file("lib/utils/json.py")

    remove_file("lib/utils/lifecycle_manager.py") # moved to lib/utils/lifecycle.py
    remove_file("Taskfile.yaml") # replaced by mise.toml
    remove_file("mise-tasks/image-bake") # moved to mise.toml
    remove_folder("lib/utils/aiohttp/logging", missing_ok=True) # unused PrintLogger, aiohttp runs through AppRunner
