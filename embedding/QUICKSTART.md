# Quick Start Guide - Embedding Module

## Overview
This embedding module vectorizes text files from the `prompt_list` directory using the bailian RemoteChat API.

## Setup

1. **Verify Configuration**
   Edit `embedding/config.yaml` and ensure:
   - `api_key` is set correctly
   - `prompt_list_dir` points to your prompt_list directory
   - `output_dir` is where you want embeddings saved

2. **Install Dependencies**
   ```bash
   pip install pyyaml requests retry
   ```

## Quick Usage

### Test the Setup
```bash
cd /home/base/APR/D4C/embedding
python test_embedder.py
```

### Process Everything
```bash
python embedder.py
```

### Process Specific Category
```bash
# List available categories
python batch_process.py --list

# Process Chart category
python batch_process.py --category Chart
```

### Process Specific Folders
Edit `config.yaml` and set:
```yaml
target_folders: ['Chart_1', 'Chart_2', 'Cli_11']
```
Then run:
```bash
python embedder.py
```

## Output

Embeddings are saved to: `embedding/vectors/`
- `{ClassName}_embeddings.json` - Embeddings for each class
- `statistics.json` - Processing statistics

## Examples

See detailed examples:
```bash
python example_usage.py 1  # Process all
python example_usage.py 2  # Process specific
python example_usage.py 3  # Single file
```

## Troubleshooting

1. **Config file not found**: Ensure you're running from the correct directory
2. **API errors**: Check your API key in config.yaml
3. **Empty results**: Verify prompt_list directory path is correct
4. **Permission errors**: Ensure output directory is writable

## Module Structure

```
embedding/
├── __init__.py           # Package initialization
├── config.yaml           # Configuration file
├── embedder.py           # Main embedding class
├── batch_process.py      # Batch processing utilities
├── example_usage.py      # Usage examples
├── test_embedder.py      # Test suite
└── README.md            # Full documentation
```

## Key Classes and Functions

- `TextEmbedder()` - Main class for embedding generation
- `process_all_classes()` - Process all or selected folders
- `process_file()` - Process a single file
- `generate_embedding()` - Generate embedding for text

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| api_key | API key for bailian | Required |
| proxy | API proxy type | bailian |
| model | Model name | deepseek-chat |
| prompt_list_dir | Input directory | ../prompt_list |
| output_dir | Output directory | ./vectors |
| file_extensions | File types to process | [.txt, .java, .py, .json] |
| target_folders | Specific folders (empty = all) | [] |

## Advanced Usage

### Custom Configuration
```python
from embedding import TextEmbedder

embedder = TextEmbedder(config_path='/path/to/custom/config.yaml')
embedder.process_all_classes()
```

### Process Single File
```python
from pathlib import Path
from embedding import TextEmbedder

embedder = TextEmbedder()
result = embedder.process_file(
    file_path=Path('/path/to/file.txt'),
    class_name='Chart_1'
)
print(result)
```

### Batch Process Range
```bash
python batch_process.py --range Closure 1 50
```

For more details, see `README.md`
