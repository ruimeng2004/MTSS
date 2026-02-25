# Troubleshooting Guide

This guide helps you resolve common issues with the D4J Fix Evaluation System.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Configuration Issues](#configuration-issues)
- [Evaluation Issues](#evaluation-issues)
- [Performance Issues](#performance-issues)
- [Error Messages](#error-messages)

## Installation Issues

### Python Version Error

**Problem**: `Python 3.8 or higher is required`

**Solution**:
```bash
# Check Python version
python3 --version

# Install Python 3.8+ if needed
# Ubuntu/Debian
sudo apt-get install python3.11

# macOS
brew install python@3.11
```

### Missing Dependencies

**Problem**: `ModuleNotFoundError: No module named 'yaml'`

**Solution**:
```bash
# Reinstall requirements
pip install -r requirements.txt

# Or install specific package
pip install pyyaml
```

### Tree-sitter Installation Failed

**Problem**: `Failed to build tree-sitter`

**Solution**:
```bash
# Install build tools first
# Ubuntu/Debian
sudo apt-get install build-essential

# macOS
xcode-select --install

# Then reinstall
pip install --upgrade tree-sitter tree-sitter-java
```

## Configuration Issues

### Config File Not Found

**Problem**: `Configuration file not found: config.yaml`

**Solution**:
```bash
# Copy example config
cp evaluation/config.example.yaml config.yaml

# Edit with your settings
vim config.yaml
```

### Invalid D4J Path

**Problem**: `D4J path does not exist: /path/to/defects4j`

**Solution**:
1. Verify Defects4J is installed:
   ```bash
   ls -la /path/to/defects4j
   ```

2. Update `config.yaml` with correct path:
   ```yaml
   evaluation_config:
     d4j_path: "/correct/path/to/defects4j"
   ```

3. Validate configuration:
   ```bash
   python -m evaluation.validate_config
   ```

### Timeout Too Short

**Problem**: Tests timing out frequently

**Solution**:
Increase timeout in `config.yaml`:
```yaml
evaluation_config:
  timeout: 1200  # Increase from 600 to 1200 seconds
```

## Evaluation Issues

### Result Folder Structure Invalid

**Problem**: `Invalid result folder structure`

**Solution**:
Ensure your result folder has this structure:
```
result_folder/
├── Chart_1/
│   ├── 1/
│   │   ├── model_output.txt
│   │   ├── query.txt
│   │   └── result.json
│   └── 2/
│       └── ...
└── Chart_2/
    └── ...
```

### Bug Checkout Failed

**Problem**: `Failed to checkout Chart_1: SVN error`

**Solution**:
1. Verify SVN is installed:
   ```bash
   svn --version
   ```

2. Check network connection

3. Try manual checkout:
   ```bash
   defects4j checkout -p Chart -v 1b -w /tmp/test_checkout
   ```

4. If manual checkout works, the issue may be temporary

### Patch Application Failed

**Problem**: `Patch application failed: git apply error`

**Solution**:
1. Check patch format in `evaluation_output/patches/`

2. Try manual application:
   ```bash
   cd workspace/Chart_1
   git apply < ../../evaluation_output/patches/Chart_1_1.patch
   ```

3. If patch is malformed, check model output parsing

### Test Execution Failed

**Problem**: `Test execution failed: compilation error`

**Solution**:
1. Verify bug compiles without patch:
   ```bash
   cd workspace/Chart_1
   defects4j compile
   ```

2. Check Java version:
   ```bash
   java -version  # Should be Java 11
   ```

3. Clean and recompile:
   ```bash
   defects4j compile -clean
   ```

## Performance Issues

### Evaluation Too Slow

**Problem**: Evaluation taking too long

**Solutions**:

1. **Enable parallel processing** (when implemented):
   ```bash
   python -m evaluation --result-folder results/ --workers 4
   ```

2. **Evaluate specific bugs only**:
   ```bash
   python -m evaluation --result-folder results/ --bugs Chart_1,Chart_2
   ```

3. **Reduce timeout**:
   ```yaml
   evaluation_config:
     timeout: 300  # Reduce from 600
   ```

4. **Use SSD for workspace**:
   ```yaml
   evaluation_config:
     workspace_dir: "/path/to/ssd/workspace"
   ```

### High Memory Usage

**Problem**: System running out of memory

**Solutions**:

1. **Reduce parallel workers**:
   ```yaml
   evaluation_config:
     parallel_workers: 1  # Sequential processing
   ```

2. **Clean workspace regularly**:
   ```bash
   rm -rf workspace/*
   ```

3. **Monitor memory usage**:
   ```bash
   # During evaluation
   watch -n 1 'ps aux | grep python | head -5'
   ```

### Disk Space Issues

**Problem**: `No space left on device`

**Solutions**:

1. **Clean workspace**:
   ```bash
   rm -rf workspace/*
   ```

2. **Clean old outputs**:
   ```bash
   rm -rf evaluation_output/old_*
   ```

3. **Use external drive**:
   ```yaml
   evaluation_config:
     workspace_dir: "/mnt/external/workspace"
     output_dir: "/mnt/external/output"
   ```

## Error Messages

### "Normalization failed: SEARCH block not found"

**Cause**: The SEARCH block in model output doesn't match source code

**Solutions**:
1. Check model output format
2. Verify source file hasn't changed
3. Review normalization reports in `evaluation_output/normalization_reports/`

### "Deprecated bug: Lang_2"

**Cause**: Bug is in deprecated list (D4J v3.0)

**Solution**: This is expected. The bug will be skipped automatically.

### "D4J environment not found"

**Cause**: Defects4J not in PATH or not installed

**Solutions**:
1. Add to PATH:
   ```bash
   export PATH="/path/to/defects4j/framework/bin:$PATH"
   ```

2. Verify installation:
   ```bash
   defects4j info
   ```

### "Permission denied: workspace/Chart_1"

**Cause**: Insufficient permissions

**Solutions**:
1. Check directory permissions:
   ```bash
   ls -la workspace/
   ```

2. Fix permissions:
   ```bash
   chmod -R u+w workspace/
   ```

3. Run with appropriate user

### "Timeout: Test execution exceeded 600 seconds"

**Cause**: Tests taking too long

**Solutions**:
1. Increase timeout in config
2. Check if tests are hanging
3. Try running tests manually:
   ```bash
   cd workspace/Chart_1
   defects4j test
   ```

## Debug Mode

Enable verbose logging for detailed information:

```bash
python -m evaluation \
    --result-folder results/ \
    --verbose \
    --log-file debug.log
```

Then check `debug.log` for detailed execution information.

## Collecting Debug Information

When reporting issues, include:

1. **System information**:
   ```bash
   python --version
   java -version
   defects4j info
   uname -a
   ```

2. **Configuration**:
   ```bash
   cat config.yaml
   ```

3. **Error logs**:
   ```bash
   tail -100 evaluation.log
   ```

4. **Test case**:
   - Minimal result folder that reproduces the issue
   - Specific bug slug and attempt number

## Getting Help

If you can't resolve the issue:

1. Check the [FAQ](FAQ.md)
2. Search existing GitHub issues
3. Create a new issue with:
   - Problem description
   - Steps to reproduce
   - Debug information (see above)
   - Expected vs actual behavior

## Common Workarounds

### Temporary Network Issues

If D4J checkout fails due to network:
```bash
# Retry with exponential backoff
for i in {1..5}; do
    python -m evaluation --result-folder results/ && break
    sleep $((2**i))
done
```

### Corrupted Workspace

If workspace gets corrupted:
```bash
# Clean and restart
rm -rf workspace/*
python -m evaluation --result-folder results/
```

### Stuck Evaluation

If evaluation appears stuck:
```bash
# Check what's running
ps aux | grep python
ps aux | grep java

# Kill if necessary
pkill -f "python -m evaluation"
```
