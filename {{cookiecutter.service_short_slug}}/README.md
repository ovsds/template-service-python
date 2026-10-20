# {{cookiecutter.service_name}}

## Usage

### Settings

#### Application

- `APP__ENV` - application environment, can be one of `development`, `testing`, `staging`, `production`. Default is `production`.
- `APP__DEBUG` - application debug mode, can be `true` or `false`. Default is `false`.

#### Logging

- `LOGS__LEVEL` - logging level, can be one of `DEBUG`, `INFO`, `WARNING`, `ERROR`. Default is `INFO`.
- `LOGS__FORMAT` - logging format string, passed to python logging formatter. Default is `%(asctime)s - %(name)s - %(levelname)s - %(message)s`.

## Development

### Global dependencies

- [mise](https://mise.jdx.dev/installing-mise.html), activated in the shell (`eval "$(mise activate zsh)"`); poetry and node come from the repository's root `mise.toml`
{%- if cookiecutter.with_trivy == 'true' %}
- [trivy](https://trivy.dev/latest/getting-started/installation/) - used for security scanning
{%- endif %}

### mise tasks

For all commands see [mise.toml](mise.toml), [mise-tasks](mise-tasks) or `mise tasks ls`.
