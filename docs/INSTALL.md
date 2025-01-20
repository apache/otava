# Installation

## Install using pipx

Hunter requires Python 3.8.  If you don't have python 3.8, use pyenv to install it.

Use pipx to install hunter:

```
pipx install git+ssh://git@github.com/datastax-labs/hunter
```

## Build Docker container

To build the Docker container, run the following command:

```bash
docker build -t hunter .
```
