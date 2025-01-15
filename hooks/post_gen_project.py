#!/usr/bin/env python
import pathlib
import shutil


def remove_folder(folder_path: str) -> None:
    folder = pathlib.Path(folder_path)
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

    if "{{ cookiecutter.with_aiohttp_utils }}" != "true":
        remove_folder("lib/utils/aiohttp")

    if "{{ cookiecutter.with_json_utils }}" != "true":
        remove_file("lib/utils/json.py")

    remove_file("lib/utils/lifecycle_manager.py") # moved to lib/utils/lifecycle.py
