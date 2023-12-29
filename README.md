# Cloud Function for background jobs

# 1.0. Setup for local development

This project uses Poetry (& pyenv to some degree) to ensure that python environments are compartmentalised to one project at a time.

## 1.1 pyenv

We strongly recommend you install [pyenv](https://github.com/pyenv/pyenv). This will let you have multiple versions of python on your system easily.

```bash
pyenv version 3.12.1
```

### 1.1.1 pyenv install MacOS

```
brew update
brew install pyenv
```

### 1.1.2 pyenv - Linux

```
git clone https://github.com/pyenv/pyenv.git ~/.pyenv
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n eval "$(pyenv init -)"\nfi' >> ~/.bashrc
```

## 1.2 Installing on MacOS

```shell
brew update
brew install pyenv openssl
pyenv install 3.12.1
curl -sSL https://install.python-poetry.org | python3 -
# Add `export PATH="$HOME/.local/bin:$PATH"` to your shell configuration file (e.g. `/Users/<username>/.zshrc`)
# may need to add python installation bin to PATH as prompted by installation
# [install gcloud](https://cloud.google.com/sdk/docs/install-sdk)
gcloud init # login with your MealHow google account and select project `mealhow-dev`
poetry self add "keyrings.google-artifactregistry-auth"
poetry shell
poetry install
```

hint: _As much as possible, please try to keep the service running locally. This makes it easier for folks on other platforms (ie. ARM64) to get it running locally._

## 1.3 Installing on Linux

### 1.3.1 Install Linux common libraries

```
sudo apt update
sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3-openssl
sudo apt install -y git openssl
```

### 1.3.2 Python + pip + Poetry versions

```
pyenv install 3.11.3
curl -sSL https://install.python-poetry.org | python3 -
# Add `export PATH="$HOME/.local/bin:$PATH"` to your shell configuration file
# [install gcloud](https://cloud.google.com/sdk/docs/install-sdk)
gcloud init # login with your Regrow google account and select project `mealhow-dev`
poetry self add "keyrings.google-artifactregistry-auth"
cd cloud-functions
poetry shell
poetry install
```

# 2.0 Installing gcloud-sdk

Based on [gcloud documentation](https://cloud.google.com/sdk/docs/install-sdk) which requires downloading the tarball and extracting it to your homedir, then install

```
./google-cloud-sdk/install.sh
gcloud init
# login through browser
# then select project `mealhow-dev` in terminal prompt
gcloud auth application-default login
# browser login again
# if you get an error about the project quota being insufficient, please check with devops, this could be a permissions error on your google account
```

## 2.1 GCP credentials

Copy credentials json in the response from `gcloud auth application-default login` to `[cloud-functions code folder]/sa.json` for use by the application.
Sometimes it ends up in `.config/gcloud/credentials.db`.

```bash
cp ~/path/to/credentials.json ~/path/to/cloud-functions/sa.json
```

# 3.0 Installing pre-commit

We use commit hooks to run a bunch of checks (typing, lint etc) which can be done locally to save debug time when the branch hits git.

## 3.1 MacOS pre-commit

```
brew install pre-commit
cd cloud-functions
pre-commit install
```

## 3.2 Linux pre-commit

```
pip install pre-commit
cd cloud-functions
pre-commit install
```

note: before issuing `pre-commit install`, make sure you are in the GIT repo directory, e.g. `cd cloud-functions`
