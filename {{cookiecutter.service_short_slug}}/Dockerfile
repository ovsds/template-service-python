ARG BASE_BUILDER_IMAGE=python:3.12.1
ARG BASE_RUNTIME_IMAGE=python:3.12.1-slim

FROM ${BASE_BUILDER_IMAGE} AS builder

RUN python -m pip install 'poetry>=1.7.0,<1.8.0'

RUN mkdir --parents /opt/app
COPY pyproject.toml /opt/app/pyproject.toml
COPY poetry.lock /opt/app/poetry.lock
COPY poetry.toml /opt/app/poetry.toml

WORKDIR /opt/app
RUN poetry install

FROM ${BASE_RUNTIME_IMAGE} AS runtime

RUN mkdir --parents /opt/app
COPY --from=builder /opt/app/.venv /opt/app/.venv
COPY bin /opt/app/bin
COPY lib /opt/app/lib

WORKDIR /opt/app
CMD [".venv/bin/python", "-m", "bin.main"]

FROM builder as builder_dev

RUN poetry install --with dev

FROM ${BASE_RUNTIME_IMAGE} as runtime_dev

RUN mkdir --parents /opt/app
COPY --from=builder_dev /opt/app/.venv /opt/app/.venv
COPY bin /opt/app/bin
COPY lib /opt/app/lib
COPY pyproject.toml /opt/app/pyproject.toml

WORKDIR /opt/app

FROM runtime_dev AS tests

COPY tests /opt/app/tests

CMD [".venv/bin/python", "-m", "pytest", "tests"]
