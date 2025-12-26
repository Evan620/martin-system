#!/usr/bin/env python3
"""
Document Ingestion Script

Batch ingest documents into the Pinecone knowledge base.

Usage:
    python scripts/ingest_documents.py --source ./data/documents --twg energy
    python scripts/ingest_documents.py --file ./policy.pdf --twg agriculture
    python scripts/ingest_documents.py --reindex
"""

import argparse
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import logging
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.core.knowledge_base import get_knowledge_base
from backend.app.utils.document_processor import get_document_processor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentIngester:
    """Handles batch document ingestion."""
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize ingester.
        
        Args:
            dry_run: If True, don't actually upload to Pinecone
        """
        self.dry_run = dry_run
        self.kb = get_knowledge_base()
        self.processor = get_document_processor()
        
        logger.info(f"Initialized DocumentIngester (dry_run={dry_run})")
    
    def scan_directory(self, directory: str) -> List[str]:
        """
        Recursively scan directory for supported documents.
        
        Args:
            directory: Path to directory
            
        Returns:
            List of file paths
        """
        supported_files = []
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if self.processor.is_supported(file_path):
                    supported_files.append(file_path)
        
        logger.info(f"Found {len(supported_files)} supported files in {directory}")
        return supported_files
    
    def ingest_file(
        self,
        file_path: str,
        twg: str,
        namespace: str = None
    ) -> Dict[str, Any]:
        """
        Ingest a single file.
        
        Args:
            file_path: Path to file
            twg: TWG identifier
            namespace: Optional Pinecone namespace
            
        Returns:
            Dict with ingestion result
        """
        try:
            logger.info(f"Ingesting: {file_path}")
            
            # Process document
            result = self.processor.process_document(
                file_path,
                additional_metadata={'twg': twg}
            )
            
            if result['status'] != 'success':
                return result
            
            # Prepare documents for Pinecone
            chunks = result['chunks']
            documents = []
            
            file_id = Path(file_path).stem
            
            for i, chunk in enumerate(chunks):
                doc = {
                    'id': f"{file_id}_chunk_{i}",
                    'text': chunk['text'],
                    'metadata': {
                        **chunk['metadata'],
                        'twg': twg,
                        'source_file': file_path
                    }
                }
                documents.append(doc)
            
            # Upload to Pinecone
            if not self.dry_run:
                namespace = namespace or f"twg-{twg}"
                upsert_result = self.kb.upsert_documents(
                    documents=documents,
                    namespace=namespace
                )
                
                logger.info(f"Uploaded {upsert_result['total_upserted']} vectors")
                
                return {
                    'file_path': file_path,
                    'status': 'success',
                    'chunks': len(documents),
                    'vectors_upserted': upsert_result['total_upserted']
                }
            else:
                logger.info(f"[DRY RUN] Would upload {len(documents)} vectors")
                return {
                    'file_path': file_path,
                    'status': 'dry_run',
                    'chunks': len(documents)
                }
            
        except Exception as e:
            logger.error(f"Error ingesting {file_path}: {e}")
            return {
                'file_path': file_path,
                'status': 'failed',
                'error': str(e)
            }
    
    def ingest_directory(
        self,
        directory: str,
        twg: str,
        namespace: str = None
    ) -> Dict[str, Any]:
        """
        Ingest all documents in a directory.
        
        Args:
            directory: Path to directory
            twg: TWG identifier
            namespace: Optional Pinecone namespace
            
        Returns:
            Dict with ingestion summary
        """
        # Scan directory
        files = self.scan_directory(directory)
        
        if not files:
            logger.warning(f"No supported files found in {directory}")
            return {
                'status': 'no_files',
                'directory': directory
            }
        
        # Ingest files with progress bar
        results = []
        successful = 0
        failed = 0
        total_chunks = 0
        
        for file_path in tqdm(files, desc="Ingesting documents"):
            result = self.ingest_file(file_path, twg, namespace)
            results.append(result)
            
            if result['status'] == 'success':
                successful += 1
                total_chunks += result.get('chunks', 0)
            elif result['status'] == 'failed':
                failed += 1
        
        summary = {
            'status': 'completed',
            'directory': directory,
            'total_files': len(files),
            'successful': successful,
            'failed': failed,
            'total_chunks': total_chunks,
            'results': results
        }
        
        logger.info(f"Ingestion complete: {successful}/{len(files)} successful")
        return summary
    
    def reindex_all(self) -> Dict[str, Any]:
        """
        Re-index entire knowledge base.
        
        This would typically:
        1. Fetch all documents from database
        2. Re-process and re-embed them
        3. Update Pinecone index
        
        Returns:
            Dict with re-indexing summary
        """
        logger.warning("Re-indexing not yet implemented")
        return {
            'status': 'not_implemented',
            'message': 'Re-indexing feature coming soon'
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Ingest documents into Pinecone knowledge base'
    )
    
    parser.add_argument(
        '--source',
        type=str,
        default='./data/test_docs',
        help='Source directory containing documents (default: ./data/test_docs)'
    )
    
    parser.add_argument(
        '--file',
        type=str,
        help='Single file to ingest'
    )
    
    parser.add_argument(
        '--twg',
        type=str,
        default='general',
        choices=['energy', 'agriculture', 'minerals', 'digital', 'protocol', 'resource_mobilization', 'general'],
        help='TWG identifier (default: general)'
    )
    
    parser.add_argument(
        '--namespace',
        type=str,
        help='Pinecone namespace (default: twg-{twg})'
    )
    
    parser.add_argument(
        '--reindex',
        action='store_true',
        help='Re-index entire knowledge base'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Process documents but don\'t upload to Pinecone'
    )
    
    args = parser.parse_args()
    
    # Initialize ingester
    ingester = DocumentIngester(dry_run=args.dry_run)
    
    # Execute ingestion
    if args.reindex:
        logger.info("Starting re-indexing...")
        result = ingester.reindex_all()
        
    elif args.file:
        logger.info(f"Ingesting single file: {args.file}")
        result = ingester.ingest_file(
            args.file,
            args.twg,
            args.namespace
        )
        
    else:
        # Default to source directory (which defaults to ./data/test_docs)
        if not os.path.exists(args.source):
            logger.error(f"Source directory not found: {args.source}")
            print(f"\nError: Source directory '{args.source}' does not exist.")
            print("Please create it or specify a different directory with --source")
            sys.exit(1)
            
        logger.info(f"Ingesting directory: {args.source}")
        result = ingester.ingest_directory(
            args.source,
            args.twg,
            args.namespace
        )
    
    # Print summary
    print("\n" + "="*60)
    print("INGESTION SUMMARY")
    print("="*60)
    
    if args.file:
        print(f"File: {result.get('file_path')}")
        print(f"Status: {result.get('status')}")
        print(f"Chunks: {result.get('chunks', 0)}")
        if result.get('status') == 'success':
            print(f"Vectors Upserted: {result.get('vectors_upserted', 0)}")
    
    elif args.source:
        print(f"Directory: {result.get('directory')}")
        print(f"Total Files: {result.get('total_files', 0)}")
        print(f"Successful: {result.get('successful', 0)}")
        print(f"Failed: {result.get('failed', 0)}")
        print(f"Total Chunks: {result.get('total_chunks', 0)}")
    
    print("="*60)
    
    # Exit with appropriate code
    if result.get('status') in ['success', 'completed', 'dry_run']:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
