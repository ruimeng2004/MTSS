#!/usr/bin/env python3
"""Vectorize patches for clustering and model selection."""

import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

sys.path.append(str(Path(__file__).resolve().parents[2]))
from utils.chat_remote import RemoteChat


def load_patches(patches_file: Path) -> List[Dict[str, Any]]:
    """Load patches from JSONL file.
    
    Args:
        patches_file: Path to patches JSONL file.
    
    Returns:
        List of patch dictionaries.
    
    Raises:
        FileNotFoundError: If patches file doesn't exist.
    """
    if not patches_file.exists():
        raise FileNotFoundError(f"Patches file not found: {patches_file}")
    
    patches = []
    with open(patches_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                patches.append(json.loads(line))
    
    return patches


def vectorize_patches(
    patches: List[Dict[str, Any]],
    api_key: str,
    model: str,
    proxy: str,
    batch_size: int = 100
) -> List[Dict[str, Any]]:
    """Vectorize patches using embedding API.
    
    Args:
        patches: List of patch dictionaries.
        api_key: API key for embedding service.
        model: Model name for embedding.
        proxy: Proxy type (bailian, OpenAI, etc.).
        batch_size: Number of patches to process before showing progress.
    
    Returns:
        List of patch dictionaries with embeddings added.
    """
    chat_client = RemoteChat(
        api_key=api_key,
        model=model,
        proxy=proxy
    )
    
    vectorized = []
    total = len(patches)
    failed = 0
    
    print(f"Vectorizing {total} patches...")
    print()
    
    for i, patch in enumerate(patches):
        item_id = patch['item_id']
        text = patch['text']
        
        try:
            embedding, tokens = chat_client.get_embedding(
                text=text,
                ID=item_id
            )
            
            if embedding:
                patch_with_embedding = patch.copy()
                patch_with_embedding['embedding'] = embedding
                patch_with_embedding['tokens'] = tokens
                vectorized.append(patch_with_embedding)
            else:
                print(f"  Warning: Failed to get embedding for {item_id}")
                failed += 1
        
        except Exception as e:
            print(f"  Error processing {item_id}: {e}")
            failed += 1
        
        if (i + 1) % batch_size == 0:
            success_rate = ((i + 1 - failed) / (i + 1)) * 100
            print(f"  Progress: {i + 1}/{total} "
                  f"({success_rate:.1f}% success)")
    
    print()
    print(f"Completed: {len(vectorized)}/{total} patches vectorized")
    if failed > 0:
        print(f"Failed: {failed} patches")
    
    return vectorized


def save_embeddings(
    embeddings: List[Dict[str, Any]],
    output_file: Path
) -> None:
    """Save embeddings to JSONL file.
    
    Args:
        embeddings: List of patch dictionaries with embeddings.
        output_file: Path to output JSONL file.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in embeddings:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"Embeddings saved to: {output_file}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Vectorize patches for clustering and model selection'
    )
    parser.add_argument(
        '--patches',
        type=str,
        default='bug_task_model_selection/data/artifacts/patches.jsonl',
        help='Path to patches JSONL file'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='bug_task_model_selection/data/vectors/patch_embeddings.jsonl',
        help='Path to output embeddings JSONL file'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        required=True,
        help='API key for embedding service'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='text-embedding-v4',
        help='Model name for embedding'
    )
    parser.add_argument(
        '--proxy',
        type=str,
        default='bailian',
        help='Proxy type (bailian, OpenAI, DeepSeek, etc.)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Progress update frequency'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of patches to process (for testing)'
    )
    
    args = parser.parse_args()
    
    try:
        patches_file = Path(args.patches)
        output_file = Path(args.output)
        
        patches = load_patches(patches_file)
        
        if args.limit:
            patches = patches[:args.limit]
            print(f"Limited to first {args.limit} patches")
        
        embeddings = vectorize_patches(
            patches=patches,
            api_key=args.api_key,
            model=args.model,
            proxy=args.proxy,
            batch_size=args.batch_size
        )
        
        if embeddings:
            save_embeddings(embeddings, output_file)
            return 0
        else:
            print("Error: No embeddings generated")
            return 1
    
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
