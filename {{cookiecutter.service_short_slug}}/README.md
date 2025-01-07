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

- [poetry](https://python-poetry.org/docs/#installation)

### Taskfile commands

For all commands see [Taskfile](Taskfile.yaml) or `task --list-all`.
