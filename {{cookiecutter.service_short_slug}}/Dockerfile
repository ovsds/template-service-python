FROM base_builder AS common_builder

RUN python -m pip install 'poetry>=1.7.0,<1.8.0'

RUN mkdir --parents /opt/app
COPY --from=sources pyproject.toml /opt/app/pyproject.toml
COPY --from=sources poetry.lock /opt/app/poetry.lock
COPY --from=sources poetry.toml /opt/app/poetry.toml

WORKDIR /opt/app
RUN poetry install

FROM base_runtime AS common_runtime

RUN mkdir --parents /opt/app
COPY --from=sources bin /opt/app/bin
COPY --from=sources lib /opt/app/lib

WORKDIR /opt/app
CMD [".venv/bin/python", "-m", "bin.main"]

FROM common_builder AS builder

FROM common_runtime AS runtime

COPY --from=builder /opt/app/.venv /opt/app/.venv

FROM common_builder AS builder_dev

RUN poetry install --with dev

FROM common_runtime AS runtime_dev

COPY --from=builder_dev /opt/app/.venv /opt/app/.venv
COPY --from=sources tests /opt/app/tests
COPY --from=sources pyproject.toml /opt/app/pyproject.toml

FROM runtime_dev AS tests_dev

CMD [".venv/bin/python", "-m", "pytest", "tests"]
