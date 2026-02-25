import os
import sys
import json
import yaml
import argparse
from pathlib import Path
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.chat_remote import RemoteChat

try:
    from embedding.vector_store import VectorStore
    VECTOR_STORE_AVAILABLE = True
except ImportError:
    VECTOR_STORE_AVAILABLE = False
    import warnings
    warnings.warn("VectorStore not available. Install cuVS dependencies for GPU-accelerated storage.")


class TextEmbedder:
    def __init__(self, config_path=None):
        if config_path is None:
            config_path = Path(__file__).parent / 'config.yaml'
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f).get('embedding_config', {})
        
        self.chat_client = RemoteChat(
            api_key=self.config['api_key'],
            model=self.config['model'],
            proxy=self.config['proxy']
        )
        
        self.output_dir = Path(self.config['output_dir'])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize vector store if enabled
        self.use_vector_store = self.config.get('use_vector_store', False)
        self.vector_store = None
        if self.use_vector_store:
            if not VECTOR_STORE_AVAILABLE:
                print("Warning: use_vector_store=True but VectorStore not available. Disabling.")
                self.use_vector_store = False
            else:
                vs_config = self.config.get('vector_store', {})
                index_path = vs_config.get('index_path', str(self.output_dir / 'vector_index'))
                self.vector_store = VectorStore(index_path, vs_config)
                print(f"Vector store initialized: {self.vector_store}")

    
    def process_file(self, file_path, class_name):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return {'file_name': file_path.name, 'status': 'failed', 'error': f'Read error: {str(e)}'}
        
        if not content:
            return {'file_name': file_path.name, 'status': 'failed', 'error': 'Empty file'}
        
        try:
            embedding, tokens = self.chat_client.get_embedding(
                text=content,
                ID=f"{class_name}_{file_path.stem}"
            )
            
            if embedding:
                return {
                    'file_name': file_path.name,
                    'status': 'success',
                    'embedding': embedding,
                    'tokens': tokens
                }
            else:
                return {'file_name': file_path.name, 'status': 'failed', 'error': 'Embedding is None'}
        except Exception as e:
            return {'file_name': file_path.name, 'status': 'failed', 'error': f'API error: {str(e)}'}
    
    def process_folders(self, folders):
        prompt_dir = Path(self.config['prompt_list_dir'])
        target_files = self.config.get('target_files', [])
        file_extensions = self.config.get('file_extensions', ['.txt'])
        
        # Collect all vectors for batch processing if using vector store
        all_vectors = []
        all_ids = []
        all_metadata = []
        
        for folder_name in folders:
            folder_path = prompt_dir / folder_name
            if not folder_path.is_dir():
                continue
            
            results = []
            for file_path in folder_path.iterdir():
                if not file_path.is_file():
                    continue
                
                if target_files and file_path.name not in target_files:
                    continue
                if not target_files and file_path.suffix not in file_extensions:
                    continue
                
                result = self.process_file(file_path, folder_name)
                results.append(result)
                
                # Collect vectors for vector store
                if self.use_vector_store and result.get('status') == 'success':
                    embedding = result['embedding']
                    vector_id = f"{folder_name}_{file_path.stem}"
                    metadata = {
                        'folder': folder_name,
                        'file_name': file_path.name,
                        'file_path': str(file_path),
                        'tokens': result.get('tokens', 0),
                    }
                    all_vectors.append(embedding)
                    all_ids.append(vector_id)
                    all_metadata.append(metadata)
            
            # Save JSON output (backward compatibility)
            output_file = self.output_dir / f"{folder_name}_embeddings.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            print(f"Processed {folder_name}: {len(results)} files")
        
        # Add vectors to vector store and build index
        if self.use_vector_store and all_vectors:
            import numpy as np
            vectors_array = np.array(all_vectors, dtype=np.float32)
            self.vector_store.add_vectors(vectors_array, all_ids, all_metadata)
            self.vector_store.build_index()
            self.vector_store.save()
            print(f"Vector store updated with {len(all_vectors)} new vectors")


def get_folders_by_prefix(prompt_dir, prefix):
    return sorted([f.name for f in prompt_dir.iterdir() 
                   if f.is_dir() and f.name.startswith(prefix)])


def get_folders_by_range(prompt_dir, category, start, end):
    all_folders = get_folders_by_prefix(prompt_dir, category)
    target = []
    for folder in all_folders:
        try:
            num = int(folder.split('_')[-1])
            if start <= num <= end:
                target.append(folder)
        except:
            continue
    return target


def main():
    parser = argparse.ArgumentParser(description='Embedding generation tool')
    parser.add_argument('--category', type=str, help='Process all folders of a category')
    parser.add_argument('--categories', type=str, nargs='+', help='Process multiple categories')
    parser.add_argument('--range', type=str, nargs=3, metavar=('CATEGORY', 'START', 'END'))
    parser.add_argument('--list', action='store_true', help='List all categories')
    
    args = parser.parse_args()
    embedder = TextEmbedder()
    prompt_dir = Path(embedder.config['prompt_list_dir'])
    
    if args.list:
        prefixes = set()
        for f in prompt_dir.iterdir():
            if f.is_dir() and '_' in f.name:
                prefixes.add(f.name.rsplit('_', 1)[0])
        
        for prefix in sorted(prefixes):
            folders = get_folders_by_prefix(prompt_dir, prefix)
            print(f"{prefix}: {len(folders)} folders")
        return
    
    folders = []
    if args.category:
        folders = get_folders_by_prefix(prompt_dir, args.category)
    elif args.categories:
        for cat in args.categories:
            folders.extend(get_folders_by_prefix(prompt_dir, cat))
    elif args.range:
        category, start, end = args.range
        folders = get_folders_by_range(prompt_dir, category, int(start), int(end))
    else:
        folders = embedder.config.get('target_folders', [])
        if not folders:
            folders = [f.name for f in prompt_dir.iterdir() if f.is_dir()]
    
    if folders:
        print(f"Processing {len(folders)} folders")
        embedder.process_folders(folders)
        print("Done!")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
