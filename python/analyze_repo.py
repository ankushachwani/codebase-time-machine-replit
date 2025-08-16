#!/usr/bin/env python3

import os
import sys
import json
import argparse
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# Import required libraries
try:
    import git
    from pydriller import Repository
    from sentence_transformers import SentenceTransformer
    import numpy as np
    import faiss
    from radon.complexity import cc_visit
    from radon.metrics import mi_visit
    import pandas as pd
    from tqdm import tqdm
    import pickle
    import hashlib
    import requests
    from urllib.parse import urlparse
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CodebaseTimeMachine:
    """Main class for analyzing git repositories and extracting semantic insights."""
    
    def __init__(self):
        self.embeddings_model = None
        self.repo_data = {}
        self.embeddings_index = None
        self.commit_embeddings = []
        self.commit_metadata = []
        
    def initialize_models(self):
        """Initialize ML models for embeddings."""
        try:
            logger.info("Initializing embedding models...")
            
            # Initialize sentence transformer for text embeddings only
            self.embeddings_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Text embedding model loaded")
            logger.info("Note: Using lightweight text embeddings for compatibility")
                
        except Exception as e:
            logger.error(f"Error initializing models: {e}")
            raise

    def clone_repository(self, repo_url: str) -> str:
        """Clone repository to temporary directory."""
        try:
            temp_dir = tempfile.mkdtemp(prefix="ctm_repo_")
            logger.info(f"Cloning repository {repo_url} to {temp_dir}")
            
            # Add better error handling for different clone failures
            try:
                # Clone repository with timeout and depth limit
                repo = git.Repo.clone_from(
                    repo_url, 
                    temp_dir,
                    depth=None,  # Get full history for analysis
                    timeout=300  # 5 minute timeout
                )
                logger.info(f"✅ Repository cloned successfully")
                
                # Verify we got commits
                commits = list(repo.iter_commits())
                logger.info(f"Found {len(commits)} commits in repository")
                
                if len(commits) == 0:
                    raise Exception("Repository appears to be empty (no commits found)")
                
                return temp_dir
                
            except git.exc.GitCommandError as git_error:
                if "Repository not found" in str(git_error) or "not found" in str(git_error).lower():
                    raise Exception(f"Repository not found or is private. Please ensure the URL is correct and the repository is public: {repo_url}")
                elif "Permission denied" in str(git_error) or "authentication" in str(git_error).lower():
                    raise Exception(f"Access denied. This repository may be private or require authentication: {repo_url}")
                else:
                    raise Exception(f"Git clone failed: {git_error}")
            
        except Exception as e:
            # Clean up temp directory if it was created
            if 'temp_dir' in locals() and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            logger.error(f"Error cloning repository: {e}")
            raise

    def analyze_repository_structure(self, repo_path: str) -> Dict[str, Any]:
        """Analyze the basic structure of the repository."""
        try:
            repo = git.Repo(repo_path)
            
            # Get basic repo info
            total_commits = len(list(repo.iter_commits()))
            total_branches = len(list(repo.branches))
            
            # Get file statistics
            file_extensions = {}
            total_files = 0
            total_lines = 0
            
            for root, dirs, files in os.walk(repo_path):
                # Skip .git directory
                if '.git' in root:
                    continue
                    
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        # Get file extension
                        ext = os.path.splitext(file)[1].lower()
                        if ext:
                            file_extensions[ext] = file_extensions.get(ext, 0) + 1
                        
                        # Count lines (for text files only)
                        if ext in ['.py', '.js', '.java', '.cpp', '.c', '.h', '.css', '.html', '.md', '.txt']:
                            try:
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    lines = len(f.readlines())
                                    total_lines += lines
                            except:
                                pass
                        
                        total_files += 1
                    except:
                        continue
            
            # Get contributor statistics
            contributors = set()
            for commit in repo.iter_commits():
                contributors.add(commit.author.email)
            
            structure_info = {
                'total_commits': total_commits,
                'total_branches': total_branches,
                'total_files': total_files,
                'total_lines': total_lines,
                'file_extensions': dict(sorted(file_extensions.items(), key=lambda x: x[1], reverse=True)[:10]),
                'contributors_count': len(contributors),
                'repository_size_mb': self.get_directory_size(repo_path) / (1024 * 1024)
            }
            
            logger.info(f"Repository structure analyzed: {structure_info}")
            return structure_info
            
        except Exception as e:
            logger.error(f"Error analyzing repository structure: {e}")
            raise

    def get_directory_size(self, path: str) -> int:
        """Calculate directory size in bytes."""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                except:
                    pass
        return total_size

    def extract_commits_data(self, repo_path: str, max_commits: int = 1000) -> List[Dict[str, Any]]:
        """Extract commit data with embeddings."""
        try:
            logger.info(f"Extracting commit data from {repo_path}")
            
            commits_data = []
            commit_count = 0
            
            # Use pydriller for detailed analysis
            for commit in tqdm(Repository(repo_path).traverse_commits(), desc="Processing commits"):
                if commit_count >= max_commits:
                    logger.info(f"Reached maximum commits limit: {max_commits}")
                    break
                
                try:
                    # Extract basic commit info
                    commit_info = {
                        'hash': commit.hash,
                        'author': commit.author.name,
                        'author_email': commit.author.email,
                        'date': commit.author_date.isoformat(),
                        'message': commit.msg.strip(),
                        'insertions': commit.insertions,
                        'deletions': commit.deletions,
                        'files_modified': len(commit.modified_files),
                        'dmm_unit_complexity': getattr(commit, 'dmm_unit_complexity', 0),
                        'dmm_unit_interfacing': getattr(commit, 'dmm_unit_interfacing', 0)
                    }
                    
                    # Extract file changes
                    file_changes = []
                    for modified_file in commit.modified_files:
                        if modified_file.filename:
                            file_change = {
                                'filename': modified_file.filename,
                                'old_path': modified_file.old_path,
                                'new_path': modified_file.new_path,
                                'change_type': str(modified_file.change_type),
                                'added_lines': modified_file.added_lines,
                                'deleted_lines': modified_file.deleted_lines
                            }
                            file_changes.append(file_change)
                    
                    commit_info['file_changes'] = file_changes
                    
                    # Create text for embedding
                    embedding_text = f"{commit_info['message']} {' '.join([f['filename'] for f in file_changes])}"
                    
                    # Generate embedding
                    if self.embeddings_model:
                        try:
                            embedding = self.embeddings_model.encode([embedding_text])[0]
                            commit_info['embedding'] = embedding.tolist()
                        except Exception as e:
                            logger.warning(f"Could not generate embedding for commit {commit.hash}: {e}")
                            commit_info['embedding'] = None
                    
                    commits_data.append(commit_info)
                    commit_count += 1
                    
                except Exception as e:
                    logger.warning(f"Error processing commit {commit.hash}: {e}")
                    continue
            
            logger.info(f"✅ Extracted {len(commits_data)} commits")
            return commits_data
            
        except Exception as e:
            logger.error(f"Error extracting commits data: {e}")
            raise

    def analyze_code_complexity(self, repo_path: str) -> Dict[str, Any]:
        """Analyze code complexity metrics."""
        try:
            logger.info("Analyzing code complexity...")
            
            complexity_data = {
                'files_analyzed': 0,
                'total_complexity': 0,
                'average_complexity': 0,
                'high_complexity_files': [],
                'maintainability_index': []
            }
            
            python_files = []
            for root, dirs, files in os.walk(repo_path):
                if '.git' in root:
                    continue
                for file in files:
                    if file.endswith('.py'):
                        python_files.append(os.path.join(root, file))
            
            for file_path in tqdm(python_files[:50], desc="Analyzing complexity"):  # Limit for performance
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        code = f.read()
                        
                    # Calculate cyclomatic complexity
                    complexity_results = cc_visit(code)
                    file_complexity = sum(c.complexity for c in complexity_results)
                    
                    # Calculate maintainability index
                    mi_results = mi_visit(code, multi=True)
                    mi_score = mi_results if isinstance(mi_results, (int, float)) else 0
                    
                    if file_complexity > 10:  # High complexity threshold
                        complexity_data['high_complexity_files'].append({
                            'file': os.path.relpath(file_path, repo_path),
                            'complexity': file_complexity
                        })
                    
                    complexity_data['total_complexity'] += file_complexity
                    complexity_data['maintainability_index'].append(mi_score)
                    complexity_data['files_analyzed'] += 1
                    
                except Exception as e:
                    logger.warning(f"Could not analyze complexity for {file_path}: {e}")
                    continue
            
            if complexity_data['files_analyzed'] > 0:
                complexity_data['average_complexity'] = complexity_data['total_complexity'] / complexity_data['files_analyzed']
                complexity_data['average_maintainability'] = np.mean(complexity_data['maintainability_index']) if complexity_data['maintainability_index'] else 0
            
            # Sort high complexity files
            complexity_data['high_complexity_files'] = sorted(
                complexity_data['high_complexity_files'], 
                key=lambda x: x['complexity'], 
                reverse=True
            )[:10]  # Top 10
            
            logger.info(f"✅ Analyzed {complexity_data['files_analyzed']} files for complexity")
            return complexity_data
            
        except Exception as e:
            logger.error(f"Error analyzing code complexity: {e}")
            return {}

    def create_embeddings_index(self, commits_data: List[Dict[str, Any]]) -> Optional[Any]:
        """Create FAISS index for semantic search."""
        try:
            logger.info("Creating embeddings index...")
            
            embeddings = []
            metadata = []
            
            for commit in commits_data:
                if commit.get('embedding'):
                    embeddings.append(commit['embedding'])
                    metadata.append({
                        'hash': commit['hash'],
                        'author': commit['author'],
                        'date': commit['date'],
                        'message': commit['message'],
                        'files_modified': commit['files_modified']
                    })
            
            if not embeddings:
                logger.warning("No embeddings found, skipping index creation")
                return None
            
            # Create FAISS index
            embeddings_array = np.array(embeddings).astype('float32')
            dimension = embeddings_array.shape[1]
            
            index = faiss.IndexFlatIP(dimension)  # Inner product for similarity
            faiss.normalize_L2(embeddings_array)  # Normalize for cosine similarity
            index.add(embeddings_array)
            
            self.embeddings_index = index
            self.commit_metadata = metadata
            
            logger.info(f"✅ Created embeddings index with {len(embeddings)} vectors")
            return index
            
        except Exception as e:
            logger.error(f"Error creating embeddings index: {e}")
            return None

    def generate_insights(self, commits_data: List[Dict[str, Any]], complexity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate high-level insights about the repository."""
        try:
            logger.info("Generating repository insights...")
            
            if not commits_data:
                return {"error": "No commits data available"}
            
            # Author activity analysis
            author_stats = {}
            monthly_activity = {}
            
            for commit in commits_data:
                author = commit['author']
                author_stats[author] = author_stats.get(author, 0) + 1
                
                # Monthly activity
                month = commit['date'][:7]  # YYYY-MM format
                monthly_activity[month] = monthly_activity.get(month, 0) + 1
            
            # Sort authors by commit count
            top_authors = sorted(author_stats.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Recent activity (last 30 commits)
            recent_commits = sorted(commits_data, key=lambda x: x['date'], reverse=True)[:30]
            recent_authors = set(commit['author'] for commit in recent_commits)
            
            # File modification patterns
            file_modification_freq = {}
            for commit in commits_data:
                for file_change in commit.get('file_changes', []):
                    filename = file_change['filename']
                    file_modification_freq[filename] = file_modification_freq.get(filename, 0) + 1
            
            most_modified_files = sorted(file_modification_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Commit message analysis
            common_keywords = {}
            for commit in commits_data:
                words = commit['message'].lower().split()
                for word in words:
                    if len(word) > 3:  # Ignore short words
                        common_keywords[word] = common_keywords.get(word, 0) + 1
            
            top_keywords = sorted(common_keywords.items(), key=lambda x: x[1], reverse=True)[:20]
            
            insights = {
                'summary': {
                    'total_commits_analyzed': len(commits_data),
                    'unique_authors': len(author_stats),
                    'active_months': len(monthly_activity),
                    'recent_active_authors': len(recent_authors)
                },
                'top_contributors': [{'author': author, 'commits': count} for author, count in top_authors],
                'most_modified_files': [{'file': file, 'modifications': count} for file, count in most_modified_files],
                'activity_timeline': dict(sorted(monthly_activity.items())),
                'common_commit_keywords': [{'keyword': word, 'frequency': count} for word, count in top_keywords],
                'complexity_insights': complexity_data
            }
            
            logger.info("✅ Generated repository insights")
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return {"error": str(e)}

    def save_analysis_results(self, repo_id: str, analysis_data: Dict[str, Any]) -> bool:
        """Save analysis results to disk for later querying."""
        try:
            # Create analysis directory
            analysis_dir = os.path.join(os.getcwd(), 'analysis_data')
            os.makedirs(analysis_dir, exist_ok=True)
            
            # Save main analysis data
            analysis_file = os.path.join(analysis_dir, f"{repo_id}_analysis.json")
            with open(analysis_file, 'w') as f:
                # Remove embeddings from commits data for JSON serialization
                clean_data = analysis_data.copy()
                if 'commits_data' in clean_data:
                    clean_commits = []
                    for commit in clean_data['commits_data']:
                        clean_commit = commit.copy()
                        if 'embedding' in clean_commit:
                            del clean_commit['embedding']
                        clean_commits.append(clean_commit)
                    clean_data['commits_data'] = clean_commits
                
                json.dump(clean_data, f, indent=2, default=str)
            
            # Save embeddings index if it exists
            if self.embeddings_index is not None:
                index_file = os.path.join(analysis_dir, f"{repo_id}_index.faiss")
                faiss.write_index(self.embeddings_index, index_file)
                
                # Save metadata
                metadata_file = os.path.join(analysis_dir, f"{repo_id}_metadata.pkl")
                with open(metadata_file, 'wb') as f:
                    pickle.dump(self.commit_metadata, f)
            
            logger.info(f"✅ Saved analysis results for {repo_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving analysis results: {e}")
            return False

    def analyze_repository(self, repo_url: str) -> Dict[str, Any]:
        """Main method to analyze a repository."""
        temp_dir = None
        try:
            # Generate repo ID
            repo_id = hashlib.md5(repo_url.encode()).hexdigest()[:12]
            
            # Initialize models
            self.initialize_models()
            
            # Clone repository
            temp_dir = self.clone_repository(repo_url)
            
            # Analyze repository structure
            structure_info = self.analyze_repository_structure(temp_dir)
            
            # Extract commits data
            commits_data = self.extract_commits_data(temp_dir)
            
            # Analyze code complexity
            complexity_data = self.analyze_code_complexity(temp_dir)
            
            # Create embeddings index
            self.create_embeddings_index(commits_data)
            
            # Generate insights
            insights = self.generate_insights(commits_data, complexity_data)
            
            # Prepare final analysis results
            analysis_results = {
                'repo_id': repo_id,
                'repo_url': repo_url,
                'analysis_timestamp': datetime.now().isoformat(),
                'structure_info': structure_info,
                'commits_data': commits_data,
                'insights': insights,
                'status': 'completed'
            }
            
            # Save results
            self.save_analysis_results(repo_id, analysis_results)
            
            # Return results without embeddings for JSON response
            clean_results = analysis_results.copy()
            if 'commits_data' in clean_results:
                clean_commits = []
                for commit in clean_results['commits_data']:
                    clean_commit = commit.copy()
                    if 'embedding' in clean_commit:
                        del clean_commit['embedding']
                    clean_commits.append(clean_commit)
                clean_results['commits_data'] = clean_commits
            
            return clean_results
            
        except Exception as e:
            logger.error(f"Error in repository analysis: {e}")
            return {
                'error': str(e),
                'status': 'failed',
                'analysis_timestamp': datetime.now().isoformat()
            }
        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Could not clean up temporary directory: {e}")

def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description='Analyze Git repository for semantic insights')
    parser.add_argument('--url', required=True, help='Git repository URL')
    parser.add_argument('--max-commits', type=int, default=1000, help='Maximum number of commits to analyze')
    
    args = parser.parse_args()
    
    try:
        # Create analyzer instance
        analyzer = CodebaseTimeMachine()
        
        # Analyze repository
        results = analyzer.analyze_repository(args.url)
        
        # Output results as JSON
        print(json.dumps(results, indent=2, default=str))
        
    except Exception as e:
        error_result = {
            'error': str(e),
            'status': 'failed',
            'analysis_timestamp': datetime.now().isoformat()
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)

if __name__ == '__main__':
    main()