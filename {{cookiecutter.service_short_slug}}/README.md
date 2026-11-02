# {{cookiecutter.service_name}}

## Usage

### Settings

#### Application

- `APP__ENV` - application environment, can be one of `development`, `testing`, `staging`, `production`. Default is `production`.
- `APP__DEBUG` - application debug mode, can be `true` or `false`. Default is `false`.
{%- if cookiecutter.__with_http_server == 'true' %}
- `APP__NAME` - application name, returned by `GET /api/v1/info`. Default is `{{ cookiecutter.service_slug }}`.
{%- endif %}

#### Logging

- `LOGS__LEVEL` - logging level, can be one of `DEBUG`, `INFO`, `WARNING`, `ERROR`. Default is `INFO`.
- `LOGS__FORMAT` - logging format string, passed to python logging formatter. Default is {%- if cookiecutter.__with_http_server == 'true' %} `%(asctime)s | %(name)s | %(levelname)s | %(request_id)s | %(message)s`{%- else %} `%(asctime)s | %(name)s | %(levelname)s | %(message)s`{%- endif %}.
{%- if cookiecutter.__with_http_server == 'true' %}

#### HTTP server

- `HTTP_SERVER__HOST` - HTTP server host. Default is `0.0.0.0`.
- `HTTP_SERVER__PORT` - HTTP server port. Default is `8080`.

Each request gets an ID from the `X-Request-ID` request header (up to 128 of `A-Za-z0-9._-`), or a generated one, returned in the `X-Request-ID` response header and available to `LOGS__FORMAT` as `%(request_id)s`.

`GET /api/v1/docs` serves a Swagger UI, which loads its assets from `cdn.jsdelivr.net`, over the OpenAPI spec at `GET /api/v1/docs/spec.json`. The spec is built from each route's handler `RequestSchema` and `ResponseSchema` and the route's `openapi_*` fields.
{%- endif %}
{%- if cookiecutter.with_prometheus == 'true' %}

### Metrics

Prometheus metrics are served at `GET /metrics`: `http_requests_total` by method, route template and status, and `http_request_duration_seconds` by method and route template. Requests matching no route, method not allowed included, share the `unmatched` route.
{%- endif %}

## Development

### Global dependencies

- [mise](https://mise.jdx.dev/installing-mise.html), activated in the shell (`eval "$(mise activate zsh)"`); poetry and node come from the repository's root `mise.toml`
{%- if cookiecutter.with_trivy == 'true' %}
- [trivy](https://trivy.dev/latest/getting-started/installation/) - used for security scanning
{%- endif %}

### mise tasks

For all commands see [mise.toml](mise.toml), [mise-tasks](mise-tasks) or `mise tasks ls`.
