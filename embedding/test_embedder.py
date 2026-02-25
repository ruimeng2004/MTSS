"""Test script for the embedding module.

This script performs basic tests to ensure the embedding module is working correctly.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from embedding import TextEmbedder


def test_initialization():
    """Test embedder initialization."""
    print("Test 1: Initialization")
    print("-" * 50)
    
    try:
        embedder = TextEmbedder()
        print("✓ TextEmbedder initialized successfully")
        print(f"  Model: {embedder.config['model']}")
        print(f"  Proxy: {embedder.config['proxy']}")
        print(f"  Output dir: {embedder.output_dir}")
        return True
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        return False


def test_config_loading():
    """Test configuration loading."""
    print("\nTest 2: Configuration Loading")
    print("-" * 50)
    
    try:
        embedder = TextEmbedder()
        required_keys = ['api_key', 'proxy', 'model', 'prompt_list_dir', 'output_dir']
        
        missing_keys = [key for key in required_keys if key not in embedder.config]
        
        if missing_keys:
            print(f"✗ Missing configuration keys: {missing_keys}")
            return False
        
        print("✓ All required configuration keys present")
        return True
    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        return False


def test_prompt_list_access():
    """Test access to prompt_list directory."""
    print("\nTest 3: Prompt List Directory Access")
    print("-" * 50)
    
    try:
        embedder = TextEmbedder()
        prompt_dir = Path(embedder.config['prompt_list_dir'])
        
        if not prompt_dir.exists():
            print(f"✗ Prompt list directory not found: {prompt_dir}")
            return False
        
        # Count directories
        class_folders = [f for f in prompt_dir.iterdir() if f.is_dir()]
        print(f"✓ Prompt list directory accessible")
        print(f"  Found {len(class_folders)} class folders")
        
        if class_folders:
            print(f"  Example folders: {', '.join([f.name for f in class_folders[:5]])}")
        
        return True
    except Exception as e:
        print(f"✗ Directory access failed: {e}")
        return False


def test_file_reading():
    """Test reading a sample file."""
    print("\nTest 4: File Reading")
    print("-" * 50)
    
    try:
        embedder = TextEmbedder()
        prompt_dir = Path(embedder.config['prompt_list_dir'])
        
        # Find first available class folder with txt files
        for class_folder in prompt_dir.iterdir():
            if class_folder.is_dir():
                txt_files = list(class_folder.glob("*.txt"))
                if txt_files:
                    test_file = txt_files[0]
                    content = embedder._read_file_content(test_file)
                    
                    if content:
                        print(f"✓ Successfully read file: {test_file.name}")
                        print(f"  Class: {class_folder.name}")
                        print(f"  Content length: {len(content)} characters")
                        print(f"  First 100 chars: {content[:100]}...")
                        return True
        
        print("✗ No readable txt files found")
        return False
        
    except Exception as e:
        print(f"✗ File reading failed: {e}")
        return False


def test_output_directory():
    """Test output directory creation."""
    print("\nTest 5: Output Directory")
    print("-" * 50)
    
    try:
        embedder = TextEmbedder()
        
        if embedder.output_dir.exists():
            print(f"✓ Output directory exists: {embedder.output_dir}")
            
            # Check if writable
            test_file = embedder.output_dir / ".test_write"
            try:
                test_file.write_text("test")
                test_file.unlink()
                print("✓ Output directory is writable")
                return True
            except Exception as e:
                print(f"✗ Output directory not writable: {e}")
                return False
        else:
            print(f"✗ Output directory not created: {embedder.output_dir}")
            return False
            
    except Exception as e:
        print(f"✗ Output directory test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 50)
    print("Embedding Module Test Suite")
    print("=" * 50)
    print()
    
    tests = [
        test_initialization,
        test_config_loading,
        test_prompt_list_access,
        test_file_reading,
        test_output_directory
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("Test Results")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print(f"✗ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
