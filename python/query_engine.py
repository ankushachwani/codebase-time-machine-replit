#!/usr/bin/env python3

import os
import sys
import json
import argparse
import pickle
from typing import Dict, List, Any, Optional
import logging

# Import required libraries
try:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer
    from datetime import datetime
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QueryEngine:
    """Query engine for semantic search over repository commit history."""
    
    def __init__(self):
        self.embeddings_model = None
        self.embeddings_index = None
        self.commit_metadata = []
        self.analysis_data = {}
        
    def initialize_model(self):
        """Initialize the sentence transformer model."""
        try:
            logger.info("Initializing query model...")
            self.embeddings_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Query model loaded")
        except Exception as e:
            logger.error(f"Error initializing model: {e}")
            raise
    
    def load_analysis_data(self, repo_id: str) -> bool:
        """Load previously analyzed repository data."""
        try:
            analysis_dir = os.path.join(os.getcwd(), 'analysis_data')
            
            # Load main analysis data
            analysis_file = os.path.join(analysis_dir, f"{repo_id}_analysis.json")
            if not os.path.exists(analysis_file):
                logger.error(f"Analysis file not found: {analysis_file}")
                return False
                
            with open(analysis_file, 'r') as f:
                self.analysis_data = json.load(f)
            
            # Load FAISS index
            index_file = os.path.join(analysis_dir, f"{repo_id}_index.faiss")
            if os.path.exists(index_file):
                self.embeddings_index = faiss.read_index(index_file)
                logger.info(f"✅ Loaded FAISS index with {self.embeddings_index.ntotal} vectors")
            else:
                logger.warning("FAISS index not found, semantic search will be limited")
            
            # Load metadata
            metadata_file = os.path.join(analysis_dir, f"{repo_id}_metadata.pkl")
            if os.path.exists(metadata_file):
                with open(metadata_file, 'rb') as f:
                    self.commit_metadata = pickle.load(f)
                logger.info(f"✅ Loaded metadata for {len(self.commit_metadata)} commits")
            else:
                logger.warning("Metadata file not found")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading analysis data: {e}")
            return False
    
    def semantic_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Perform semantic search over commit history."""
        try:
            if not self.embeddings_model or not self.embeddings_index:
                logger.warning("Embeddings model or index not available")
                return []
            
            # Generate query embedding
            query_embedding = self.embeddings_model.encode([query])
            query_embedding = query_embedding.astype('float32')
            faiss.normalize_L2(query_embedding)
            
            # Search in FAISS index
            similarities, indices = self.embeddings_index.search(query_embedding, top_k)
            
            results = []
            for i, idx in enumerate(indices[0]):
                if idx >= 0 and idx < len(self.commit_metadata):
                    result = self.commit_metadata[idx].copy()
                    result['similarity_score'] = float(similarities[0][i])
                    result['rank'] = i + 1
                    results.append(result)
            
            logger.info(f"Found {len(results)} semantic search results for: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    def keyword_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Perform keyword-based search over commit messages and file names."""
        try:
            if not self.analysis_data.get('commits_data'):
                return []
            
            query_keywords = query.lower().split()
            results = []
            
            for commit in self.analysis_data['commits_data']:
                score = 0
                commit_text = (commit.get('message', '') + ' ' + 
                              ' '.join([f.get('filename', '') for f in commit.get('file_changes', [])])).lower()
                
                # Calculate keyword match score
                for keyword in query_keywords:
                    if keyword in commit_text:
                        score += commit_text.count(keyword)
                
                if score > 0:
                    result = {
                        'hash': commit.get('hash', ''),
                        'author': commit.get('author', ''),
                        'date': commit.get('date', ''),
                        'message': commit.get('message', ''),
                        'files_modified': commit.get('files_modified', 0),
                        'keyword_score': score,
                        'file_changes': commit.get('file_changes', [])[:3]  # Limit to 3 files
                    }
                    results.append(result)
            
            # Sort by keyword score
            results = sorted(results, key=lambda x: x['keyword_score'], reverse=True)[:top_k]
            
            logger.info(f"Found {len(results)} keyword search results for: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            return []
    
    def author_search(self, query: str) -> List[Dict[str, Any]]:
        """Search for commits by specific author."""
        try:
            if not self.analysis_data.get('commits_data'):
                return []
            
            query_lower = query.lower()
            results = []
            
            for commit in self.analysis_data['commits_data']:
                author_name = commit.get('author', '').lower()
                author_email = commit.get('author_email', '').lower()
                
                if query_lower in author_name or query_lower in author_email:
                    result = {
                        'hash': commit.get('hash', ''),
                        'author': commit.get('author', ''),
                        'author_email': commit.get('author_email', ''),
                        'date': commit.get('date', ''),
                        'message': commit.get('message', ''),
                        'files_modified': commit.get('files_modified', 0),
                        'insertions': commit.get('insertions', 0),
                        'deletions': commit.get('deletions', 0)
                    }
                    results.append(result)
            
            # Sort by date (most recent first)
            results = sorted(results, key=lambda x: x['date'], reverse=True)
            
            logger.info(f"Found {len(results)} commits by author matching: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error in author search: {e}")
            return []
    
    def file_search(self, query: str) -> List[Dict[str, Any]]:
        """Search for commits that modified specific files."""
        try:
            if not self.analysis_data.get('commits_data'):
                return []
            
            query_lower = query.lower()
            results = []
            
            for commit in self.analysis_data['commits_data']:
                matching_files = []
                
                for file_change in commit.get('file_changes', []):
                    filename = file_change.get('filename', '').lower()
                    if query_lower in filename:
                        matching_files.append(file_change)
                
                if matching_files:
                    result = {
                        'hash': commit.get('hash', ''),
                        'author': commit.get('author', ''),
                        'date': commit.get('date', ''),
                        'message': commit.get('message', ''),
                        'matching_files': matching_files,
                        'total_files_modified': commit.get('files_modified', 0)
                    }
                    results.append(result)
            
            # Sort by date (most recent first)
            results = sorted(results, key=lambda x: x['date'], reverse=True)
            
            logger.info(f"Found {len(results)} commits modifying files matching: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error in file search: {e}")
            return []
    
    def time_range_search(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Search for commits within a specific time range."""
        try:
            if not self.analysis_data.get('commits_data'):
                return []
            
            results = []
            
            for commit in self.analysis_data['commits_data']:
                commit_date = commit.get('date', '')
                if start_date <= commit_date <= end_date:
                    result = {
                        'hash': commit.get('hash', ''),
                        'author': commit.get('author', ''),
                        'date': commit.get('date', ''),
                        'message': commit.get('message', ''),
                        'files_modified': commit.get('files_modified', 0),
                        'insertions': commit.get('insertions', 0),
                        'deletions': commit.get('deletions', 0)
                    }
                    results.append(result)
            
            # Sort by date (most recent first)
            results = sorted(results, key=lambda x: x['date'], reverse=True)
            
            logger.info(f"Found {len(results)} commits between {start_date} and {end_date}")
            return results
            
        except Exception as e:
            logger.error(f"Error in time range search: {e}")
            return []
    
    def get_repository_summary(self) -> Dict[str, Any]:
        """Get a summary of the analyzed repository."""
        try:
            if not self.analysis_data:
                return {}
            
            summary = {
                'repo_info': {
                    'repo_id': self.analysis_data.get('repo_id', ''),
                    'repo_url': self.analysis_data.get('repo_url', ''),
                    'analysis_timestamp': self.analysis_data.get('analysis_timestamp', ''),
                    'status': self.analysis_data.get('status', 'unknown')
                },
                'structure_info': self.analysis_data.get('structure_info', {}),
                'insights': self.analysis_data.get('insights', {}),
                'search_capabilities': {
                    'semantic_search_available': self.embeddings_index is not None,
                    'total_commits_indexed': len(self.commit_metadata),
                    'search_types': ['semantic', 'keyword', 'author', 'file', 'time_range']
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting repository summary: {e}")
            return {}
    
    def process_query(self, query: str, repo_id: str, search_type: str = 'auto') -> Dict[str, Any]:
        """Main method to process different types of queries."""
        try:
            # Load analysis data if not already loaded
            if not self.analysis_data:
                if not self.load_analysis_data(repo_id):
                    return {
                        'error': f'Repository analysis not found for ID: {repo_id}',
                        'suggestions': ['Please analyze the repository first', 'Check if the repository ID is correct']
                    }
            
            # Initialize model if not already done
            if not self.embeddings_model:
                self.initialize_model()
            
            results = {
                'query': query,
                'repo_id': repo_id,
                'search_type': search_type,
                'timestamp': datetime.now().isoformat(),
                'results': []
            }
            
            # Determine search strategy
            query_lower = query.lower()
            
            if search_type == 'auto':
                # Auto-detect query type
                if 'author' in query_lower or 'who' in query_lower:
                    search_type = 'author'
                elif 'file' in query_lower or '.py' in query_lower or '.js' in query_lower:
                    search_type = 'file'
                elif any(date_term in query_lower for date_term in ['before', 'after', 'during', '2020', '2021', '2022', '2023', '2024']):
                    search_type = 'time_range'
                else:
                    search_type = 'semantic'
            
            # Execute appropriate search
            if search_type == 'semantic':
                results['results'] = self.semantic_search(query)
                results['search_type'] = 'semantic'
                
            elif search_type == 'keyword':
                results['results'] = self.keyword_search(query)
                results['search_type'] = 'keyword'
                
            elif search_type == 'author':
                # Extract author name from query
                author_query = query.lower().replace('author', '').replace('who', '').strip()
                results['results'] = self.author_search(author_query)
                results['search_type'] = 'author'
                
            elif search_type == 'file':
                # Extract filename from query
                file_query = query.lower().replace('file', '').replace('modified', '').strip()
                results['results'] = self.file_search(file_query)
                results['search_type'] = 'file'
                
            elif search_type == 'summary':
                summary = self.get_repository_summary()
                results['summary'] = summary
                results['search_type'] = 'summary'
                
            else:
                # Default to combined semantic + keyword search
                semantic_results = self.semantic_search(query, 5)
                keyword_results = self.keyword_search(query, 5)
                
                # Combine and deduplicate results
                all_results = semantic_results + keyword_results
                seen_hashes = set()
                unique_results = []
                
                for result in all_results:
                    result_hash = result.get('hash', '')
                    if result_hash and result_hash not in seen_hashes:
                        seen_hashes.add(result_hash)
                        unique_results.append(result)
                
                results['results'] = unique_results[:10]  # Top 10
                results['search_type'] = 'combined'
            
            # Add suggestions if no results found
            if not results.get('results') and not results.get('summary'):
                results['suggestions'] = [
                    f'Try a broader search term',
                    f'Use specific keywords from commit messages',
                    f'Search by author name or file extension',
                    f'Use "summary" to get repository overview'
                ]
            
            # Add metadata
            results['total_results'] = len(results.get('results', []))
            results['repository_info'] = {
                'total_commits_available': len(self.analysis_data.get('commits_data', [])),
                'analysis_date': self.analysis_data.get('analysis_timestamp', ''),
                'repo_url': self.analysis_data.get('repo_url', '')
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                'error': str(e),
                'query': query,
                'repo_id': repo_id,
                'timestamp': datetime.now().isoformat()
            }

def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description='Query repository analysis for semantic insights')
    parser.add_argument('--query', required=True, help='Search query')
    parser.add_argument('--repo-id', required=True, help='Repository ID from analysis')
    parser.add_argument('--search-type', default='auto', 
                       choices=['auto', 'semantic', 'keyword', 'author', 'file', 'summary'],
                       help='Type of search to perform')
    
    args = parser.parse_args()
    
    try:
        # Create query engine instance
        query_engine = QueryEngine()
        
        # Process query
        results = query_engine.process_query(args.query, args.repo_id, args.search_type)
        
        # Output results as JSON
        print(json.dumps(results, indent=2, default=str))
        
    except Exception as e:
        error_result = {
            'error': str(e),
            'query': args.query,
            'repo_id': args.repo_id,
            'timestamp': datetime.now().isoformat()
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)

if __name__ == '__main__':
    main()