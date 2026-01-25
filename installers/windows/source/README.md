# Source Installation (Windows)

## Quick Start

Double-click `install.bat` or:

```cmd
install.bat
```

## What it does

1. Clones repository to `%USERPROFILE%\.vibesrails`
2. Installs in development mode

## After Installation

```cmd
cd your-project
vibesrails --setup
```

## Update

```cmd
cd %USERPROFILE%\.vibesrails
git pull
pip install -e .
```

## Fresh Install

```cmd
rmdir /s /q %USERPROFILE%\.vibesrails
install.bat
```
