# Installation Guide

This guide will help you install and set up the D4J Fix Evaluation System.

## Prerequisites

### System Requirements

- **Operating System**: Linux or macOS (Windows with WSL2)
- **Python**: 3.8 or higher
- **Java**: Java 11 (required by Defects4J)
- **Perl**: 5.0.12 or higher
- **Git**: 1.9 or higher
- **SVN**: 1.8 or higher

### Disk Space

- Minimum: 10 GB (for basic evaluation)
- Recommended: 50 GB (for full evaluation with multiple bugs)

## Step 1: Install System Dependencies

### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install -y \
    python3 python3-pip \
    openjdk-11-jdk \
    perl \
    git \
    subversion \
    cpanminus
```

### macOS

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 openjdk@11 perl git subversion
```

### Verify Java Installation

```bash
java -version
# Should show: openjdk version "11.x.x"
```

## Step 2: Install Defects4J

### Download and Install

```bash
# Clone Defects4J repository
git clone https://github.com/rjust/defects4j.git /path/to/defects4j

# Initialize Defects4J
cd /path/to/defects4j
cpanm --installdeps .
./init.sh

# Add to PATH
export PATH="/path/to/defects4j/framework/bin:$PATH"
export D4J_HOME="/path/to/defects4j"

# Add to your shell profile (~/.bashrc or ~/.zshrc)
echo 'export PATH="/path/to/defects4j/framework/bin:$PATH"' >> ~/.bashrc
echo 'export D4J_HOME="/path/to/defects4j"' >> ~/.bashrc
source ~/.bashrc
```

### Verify Defects4J Installation

```bash
defects4j info -p Lang
# Should display information about the Lang project
```

## Step 3: Install Python Dependencies

### Clone the Repository

```bash
git clone <repository-url>
cd MTSS
```

### Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Linux/macOS
# or
venv\Scripts\activate  # On Windows
```

### Install Python Packages

```bash
# Install requirements
pip install -r requirements.txt

# Verify installation
python -c "import yaml, tree_sitter; print('Dependencies installed successfully')"
```

## Step 4: Configure the System

### Copy Example Configuration

```bash
cp evaluation/config.example.yaml config.yaml
```

### Edit Configuration

Open `config.yaml` and update the following:

```yaml
evaluation_config:
  # Update this to your Defects4J installation path
  d4j_path: "/path/to/defects4j"
  
  # Optional: customize other settings
  workspace_dir: "./workspace"
  output_dir: "./evaluation_output"
  timeout: 600
  parallel_workers: 4
```

### Validate Configuration

```bash
python -m evaluation.validate_config
```

Expected output:
```
================================================================================
D4J Fix Evaluation System - Configuration Validation
================================================================================

1. Validating configuration file...
INFO: ✓ Configuration file loaded successfully
INFO: ✓ Configuration structure is valid
INFO: ✓ D4J path exists: /path/to/defects4j
...

================================================================================
✓ All validations passed!
================================================================================
```

## Step 5: Verify Installation

Run the setup verification script:

```bash
python -m evaluation.verify_setup
```

This will check:
- Python version
- Required packages
- Defects4J installation
- Configuration file

## Troubleshooting

### Issue: "defects4j: command not found"

**Solution**: Add Defects4J to your PATH:
```bash
export PATH="/path/to/defects4j/framework/bin:$PATH"
```

### Issue: "Java version mismatch"

**Solution**: Ensure Java 11 is installed and set as default:
```bash
# Check Java version
java -version

# On Ubuntu, switch Java version
sudo update-alternatives --config java
```

### Issue: "tree-sitter not found"

**Solution**: Reinstall tree-sitter packages:
```bash
pip uninstall tree-sitter tree-sitter-java
pip install tree-sitter tree-sitter-java
```

### Issue: "Permission denied" when running defects4j

**Solution**: Make sure the defects4j scripts are executable:
```bash
chmod +x /path/to/defects4j/framework/bin/defects4j
```

### Issue: "SVN checkout failed"

**Solution**: Install SVN and verify it's in PATH:
```bash
# Ubuntu/Debian
sudo apt-get install subversion

# macOS
brew install subversion

# Verify
svn --version
```

## Next Steps

After successful installation:

1. **Read the User Guide**: See `evaluation/README.md` for usage instructions
2. **Run a Test Evaluation**: Try evaluating a small result folder
3. **Check the Examples**: See `evaluation/examples/` for sample usage

## Getting Help

If you encounter issues:

1. Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Review the [FAQ](FAQ.md)
3. Open an issue on GitHub

## Uninstallation

To remove the evaluation system:

```bash
# Remove virtual environment
rm -rf venv

# Remove workspace and output directories
rm -rf workspace evaluation_output

# Optionally remove Defects4J
rm -rf /path/to/defects4j
```
