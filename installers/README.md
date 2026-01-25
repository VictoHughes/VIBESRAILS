# vibesrails Installers

Choose your installation method:

| Method | Use Case | Platforms |
|--------|----------|-----------|
| **[pip](./pip/)** | Standard installation | All |
| **[source](./source/)** | Development / latest features | All |
| **[claude-code](./claude-code/)** | Full Claude Code integration | All |

## Quick Install

### pip (recommended)

```bash
pip install vibesrails
```

### From source

**Unix/Mac:**
```bash
./source/install.sh
```

**Windows:**
```cmd
source\install.bat
```

**Cross-platform:**
```bash
python source/install.py
```

### With Claude Code integration

**Unix/Mac:**
```bash
cd your-project
/path/to/claude-code/install.sh
```

**Windows:**
```cmd
cd your-project
\path\to\claude-code\install.bat
```

**Cross-platform:**
```bash
cd your-project
python /path/to/claude-code/install.py
```

## After Installation

```bash
cd your-project
vibesrails --setup
```

## Requirements

- Python 3.10+
- pip
- git (for pre-commit hooks and source install)

## Platform Support

| Platform | Shell Script | Batch Script | Python Script |
|----------|--------------|--------------|---------------|
| Linux | `.sh` | - | `.py` |
| macOS | `.sh` | - | `.py` |
| Windows | - | `.bat` | `.py` |

The Python scripts (`install.py`) work on all platforms.
