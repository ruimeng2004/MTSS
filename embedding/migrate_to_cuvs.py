"""
Migrate existing JSON embeddings to cuVS vector store
"""
import os
import sys
import json
import argparse
import numpy as np
from pathlib import Path
from tqdm import tqdm

sys.path.append(str(Path(__file__).parent.parent))

from embedding.vector_store import VectorStore


def load_json_embeddings(json_file):
    """Load embeddings from JSON file"""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    vectors = []
    ids = []
    metadata = []
    
    for item in data:
        if item.get('status') == 'success' and 'embedding' in item:
            vectors.append(item['embedding'])
            
            # Create ID from file name
            file_name = item['file_name']
            folder_name = json_file.stem.replace('_embeddings', '')
            vec_id = f"{folder_name}_{Path(file_name).stem}"
            ids.append(vec_id)
            
            # Store metadata
            meta = {
                'folder': folder_name,
                'file_name': file_name,
                'tokens': item.get('tokens', 0),
                'source_file': str(json_file),
            }
            metadata.append(meta)
    
    return vectors, ids, metadata


def migrate_directory(source_dir, vector_store_config):
    """Migrate all JSON embeddings from a directory to vector store"""
    source_path = Path(source_dir)
    
    if not source_path.exists():
        print(f"Error: Source directory does not exist: {source_dir}")
        return
    
    # Find all embedding JSON files
    json_files = list(source_path.glob("*_embeddings.json"))
    
    if not json_files:
        print(f"No embedding JSON files found in {source_dir}")
        return
    
    print(f"Found {len(json_files)} JSON embedding files")
    
    # Initialize vector store
    index_path = vector_store_config.get('index_path', str(source_path.parent / 'vector_index'))
    vs = VectorStore(index_path, vector_store_config)
    
    # Process each JSON file
    total_vectors = 0
    all_vectors = []
    all_ids = []
    all_metadata = []
    
    print("\nLoading embeddings from JSON files...")
    for json_file in tqdm(json_files, desc="Loading"):
        try:
            vectors, ids, metadata = load_json_embeddings(json_file)
            all_vectors.extend(vectors)
            all_ids.extend(ids)
            all_metadata.extend(metadata)
            total_vectors += len(vectors)
        except Exception as e:
            print(f"\nError processing {json_file.name}: {e}")
    
    if not all_vectors:
        print("No valid vectors found in JSON files")
        return
    
    print(f"\nTotal vectors to migrate: {total_vectors}")
    
    # Convert to numpy array
    print("Converting to numpy array...")
    vectors_array = np.array(all_vectors, dtype=np.float32)
    
    # Add to vector store
    print("Adding vectors to vector store...")
    vs.add_vectors(vectors_array, all_ids, all_metadata)
    
    # Build index
    print("Building index (this may take a while for large datasets)...")
    vs.build_index()
    
    # Save
    print("Saving vector store...")
    vs.save()
    
    print(f"\n✓ Migration completed!")
    print(f"  - Vectors migrated: {total_vectors}")
    print(f"  - Index path: {index_path}")
    print(f"  - Vector store: {vs}")
    
    return vs


def verify_migration(vector_store, sample_size=10):
    """Verify migration by testing searches"""
    print(f"\nVerifying migration with {sample_size} random searches...")
    
    all_ids = vector_store.get_all_ids()
    if not all_ids:
        print("No vectors in store to verify")
        return
    
    import random
    sample_ids = random.sample(all_ids, min(sample_size, len(all_ids)))
    
    success_count = 0
    for vec_id in sample_ids:
        vec = vector_store.get_vector(vec_id)
        if vec is not None:
            results = vector_store.search(vec, k=5)
            # The first result should be the vector itself (distance ~0)
            if results and results[0][0] == vec_id and results[0][1] < 0.01:
                success_count += 1
    
    accuracy = success_count / len(sample_ids) * 100
    print(f"Verification: {success_count}/{len(sample_ids)} searches successful ({accuracy:.1f}%)")
    
    if accuracy == 100:
        print("✓ Migration verified successfully!")
    else:
        print("⚠ Some verification tests failed")


def main():
    parser = argparse.ArgumentParser(description='Migrate JSON embeddings to cuVS vector store')
    parser.add_argument('source_dir', help='Directory containing JSON embedding files')
    parser.add_argument('--index-path', help='Path to store vector index')
    parser.add_argument('--index-type', default='ivf_flat', 
                       choices=['ivf_flat', 'ivf_pq', 'cagra'],
                       help='Index type (default: ivf_flat)')
    parser.add_argument('--metric', default='l2',
                       choices=['l2', 'inner_product'],
                       help='Distance metric (default: l2)')
    parser.add_argument('--nlist', type=int, default=100,
                       help='Number of clusters for IVF index')
    parser.add_argument('--nprobe', type=int, default=10,
                       help='Number of clusters to search')
    parser.add_argument('--verify', action='store_true',
                       help='Verify migration with sample searches')
    
    args = parser.parse_args()
    
    # Build configuration
    config = {
        'index_type': args.index_type,
        'metric': args.metric,
        'nlist': args.nlist,
        'nprobe': args.nprobe,
    }
    
    if args.index_path:
        config['index_path'] = args.index_path
    
    # Run migration
    vs = migrate_directory(args.source_dir, config)
    
    # Verify if requested
    if vs and args.verify:
        verify_migration(vs)


if __name__ == '__main__':
    main()
