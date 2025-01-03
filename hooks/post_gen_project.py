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

    remove_file("lib/utils/lifecycle_manager.py") # moved to lib/utils/lifecycle.py
