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
    import numpy as np
    from radon.complexity import cc_visit
    from radon.metrics import mi_visit
    import pandas as pd
    from tqdm import tqdm
    import hashlib
    from collections import Counter
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    print("Please run: pip install GitPython pydriller radon numpy pandas tqdm")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleCodebaseAnalyzer:
    """Simplified analyzer that works without heavy ML dependencies."""
    
    def __init__(self):
        self.repo_data = {}
        
    def clone_repository(self, repo_url: str) -> str:
        """Clone repository to temporary directory."""
        try:
            temp_dir = tempfile.mkdtemp(prefix="ctm_repo_")
            logger.info(f"Cloning repository {repo_url} to {temp_dir}")
            
            try:
                # Clone repository (remove timeout as it's causing issues)
                repo = git.Repo.clone_from(repo_url, temp_dir)
                logger.info(f"✅ Repository cloned successfully")
                
                # Verify we got commits
                commits = list(repo.iter_commits())
                logger.info(f"Found {len(commits)} commits in repository")
                
                if len(commits) == 0:
                    raise Exception("Repository appears to be empty (no commits found)")
                
                return temp_dir
                
            except git.exc.GitCommandError as git_error:
                error_msg = str(git_error).lower()
                if "repository not found" in error_msg or "not found" in error_msg:
                    raise Exception(f"Repository not found or is private. Please ensure the URL is correct and the repository is public: {repo_url}")
                elif "permission denied" in error_msg or "authentication" in error_msg:
                    raise Exception(f"Access denied. This repository may be private or require authentication: {repo_url}")
                elif "timeout" in error_msg:
                    raise Exception(f"Repository clone timed out. The repository may be too large or network connection is slow: {repo_url}")
                else:
                    raise Exception(f"Git clone failed: {git_error}")
            
        except Exception as e:
            # Clean up temp directory if it was created
            if 'temp_dir' in locals() and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
            logger.error(f"Error cloning repository: {e}")
            raise

    def analyze_repository_structure(self, repo_path: str) -> Dict[str, Any]:
        """Analyze the basic structure of the repository."""
        try:
            repo = git.Repo(repo_path)
            
            # Get basic repo info
            commits_list = list(repo.iter_commits())
            total_commits = len(commits_list)
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
                        if ext in ['.py', '.js', '.java', '.cpp', '.c', '.h', '.css', '.html', '.md', '.txt', '.jsx', '.ts', '.tsx']:
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
            for commit in commits_list:
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
            
            logger.info(f"Repository structure analyzed: {total_commits} commits, {len(contributors)} contributors, {total_files} files")
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
        """Extract commit data without embeddings."""
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
            
            # Find Python and JavaScript files
            code_files = []
            for root, dirs, files in os.walk(repo_path):
                if '.git' in root:
                    continue
                for file in files:
                    if file.endswith(('.py', '.js', '.jsx', '.ts', '.tsx')):
                        code_files.append(os.path.join(root, file))
            
            for file_path in tqdm(code_files[:50], desc="Analyzing complexity"):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        code = f.read()
                        
                    # Only analyze Python files for complexity (radon doesn't support JS)
                    if file_path.endswith('.py'):
                        # Calculate cyclomatic complexity
                        complexity_results = cc_visit(code)
                        file_complexity = sum(c.complexity for c in complexity_results)
                        
                        # Calculate maintainability index
                        mi_results = mi_visit(code, multi=True)
                        mi_score = mi_results if isinstance(mi_results, (int, float)) else 0
                        
                        if file_complexity > 10:
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
            )[:10]
            
            logger.info(f"✅ Analyzed {complexity_data['files_analyzed']} files for complexity")
            return complexity_data
            
        except Exception as e:
            logger.error(f"Error analyzing code complexity: {e}")
            return {}

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
    
    def extract_commits_data(self, repo_path: str) -> List[Dict[str, Any]]:
        """Extract commits data from a local repository path."""
        try:
            from pydriller import Repository
            
            commits_data = []
            logger.info(f"Extracting commits from {repo_path}")
            
            for commit in Repository(repo_path).traverse_commits():
                if len(commits_data) >= 500:  # Limit commits
                    break
                    
                commit_info = {
                    'hash': commit.hash,
                    'author': commit.author.name,
                    'author_email': commit.author.email,
                    'date': commit.author_date.isoformat(),
                    'message': commit.msg,
                    'files_modified': len(commit.modified_files),
                    'insertions': commit.insertions,
                    'deletions': commit.deletions,
                    'file_changes': []
                }
                
                # Add file changes info
                for modified_file in commit.modified_files:
                    if len(commit_info['file_changes']) < 10:  # Limit files per commit
                        commit_info['file_changes'].append({
                            'filename': modified_file.filename,
                            'status': modified_file.change_type.name.lower(),
                            'insertions': modified_file.added_lines,
                            'deletions': modified_file.deleted_lines
                        })
                
                commits_data.append(commit_info)
            
            logger.info(f"✅ Extracted {len(commits_data)} commits")
            return commits_data
            
        except Exception as e:
            logger.error(f"Error extracting commits data: {e}")
            return []
    
    def extract_code_content(self, repo_path: str, max_files: int = 50) -> Dict[str, Any]:
        """Extract actual code content from files for AI analysis."""
        try:
            logger.info(f"Extracting code content from {repo_path}")
            
            code_content = {
                'files': [],
                'total_files_analyzed': 0,
                'total_lines_analyzed': 0
            }
            
            # Define code file extensions to analyze
            code_extensions = {
                '.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.h', 
                '.cs', '.go', '.rs', '.php', '.rb', '.ts', '.jsx', '.vue',
                '.sql', '.sh', '.yaml', '.yml', '.json', '.xml', '.md'
            }
            
            files_processed = 0
            
            # Walk through all files in the repository
            for root, dirs, files in os.walk(repo_path):
                # Skip hidden directories and common ignore patterns
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', 'env', 'dist', 'build']]
                
                for file in files:
                    if files_processed >= max_files:
                        break
                        
                    file_path = os.path.join(root, file)
                    file_ext = os.path.splitext(file)[1].lower()
                    
                    if file_ext in code_extensions and not file.startswith('.'):
                        try:
                            # Get relative path from repo root
                            rel_path = os.path.relpath(file_path, repo_path)
                            
                            # Read file content (limit size to prevent memory issues)
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                
                            # Limit content size (first 5000 chars per file)
                            if len(content) > 5000:
                                content = content[:5000] + "\\n... (truncated)"
                                
                            # Count lines
                            line_count = len(content.split('\\n'))
                            
                            file_info = {
                                'filename': rel_path,
                                'extension': file_ext,
                                'size_lines': line_count,
                                'content': content,
                                'size_chars': len(content)
                            }
                            
                            code_content['files'].append(file_info)
                            code_content['total_lines_analyzed'] += line_count
                            files_processed += 1
                            
                        except Exception as e:
                            logger.warning(f"Could not read file {file_path}: {e}")
                            continue
                
                if files_processed >= max_files:
                    break
            
            code_content['total_files_analyzed'] = files_processed
            logger.info(f"✅ Extracted content from {files_processed} files ({code_content['total_lines_analyzed']} lines)")
            
            return code_content
            
        except Exception as e:
            logger.error(f"Error extracting code content: {e}")
            return {'files': [], 'total_files_analyzed': 0, 'total_lines_analyzed': 0}

    def save_analysis_results(self, repo_id: str, analysis_data: Dict[str, Any]) -> bool:
        """Save analysis results to disk for later querying."""
        try:
            # Create analysis directory
            analysis_dir = os.path.join(os.getcwd(), 'analysis_data')
            os.makedirs(analysis_dir, exist_ok=True)
            
            # Save main analysis data
            analysis_file = os.path.join(analysis_dir, f"{repo_id}_analysis.json")
            with open(analysis_file, 'w') as f:
                json.dump(analysis_data, f, indent=2, default=str)
            
            logger.info(f"✅ Saved analysis results for {repo_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving analysis results: {e}")
            return False

    def analyze_repository(self, repo_url: str, max_commits: int = 1000) -> Dict[str, Any]:
        """Main method to analyze a repository."""
        temp_dir = None
        try:
            # Generate repo ID
            repo_id = hashlib.md5(repo_url.encode()).hexdigest()[:12]
            
            # Clone repository
            temp_dir = self.clone_repository(repo_url)
            
            # Analyze repository structure
            structure_info = self.analyze_repository_structure(temp_dir)
            
            # Extract commits data
            commits_data = self.extract_commits_data(temp_dir, max_commits)
            
            # Analyze code complexity
            complexity_data = self.analyze_code_complexity(temp_dir)
            
            # Extract actual code content
            code_content = self.extract_code_content(temp_dir)
            
            # Generate insights
            insights = self.generate_insights(commits_data, complexity_data)
            
            # Prepare final analysis results
            analysis_results = {
                'repo_id': repo_id,
                'repo_url': repo_url,
                'analysis_timestamp': datetime.now().isoformat(),
                'structure_info': structure_info,
                'commits_data': commits_data,
                'code_content': code_content,
                'insights': insights,
                'analysis_type': 'simple',
                'note': 'Analysis performed without ML embeddings for compatibility',
                'status': 'completed'
            }
            
            # Save results
            self.save_analysis_results(repo_id, analysis_results)
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error in repository analysis: {e}")
            return {
                'error': str(e),
                'status': 'failed',
                'analysis_timestamp': datetime.now().isoformat(),
                'repo_url': repo_url
            }
        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Could not clean up temporary directory: {e}")

    def analyze_repository_structure(self, repo_path: str) -> Dict[str, Any]:
        """Analyze the basic structure of the repository."""
        try:
            repo = git.Repo(repo_path)
            
            # Get basic repo info
            commits_list = list(repo.iter_commits())
            total_commits = len(commits_list)
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
                        if ext in ['.py', '.js', '.java', '.cpp', '.c', '.h', '.css', '.html', '.md', '.txt', '.jsx', '.ts', '.tsx']:
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
            for commit in commits_list:
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
            
            logger.info(f"Repository structure analyzed: {total_commits} commits, {len(contributors)} contributors, {total_files} files")
            return structure_info
            
        except Exception as e:
            logger.error(f"Error analyzing repository structure: {e}")
            raise

    def extract_commits_data(self, repo_path: str, max_commits: int = 1000) -> List[Dict[str, Any]]:
        """Extract commit data without embeddings."""
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
            
            # Find Python files (radon only supports Python)
            python_files = []
            for root, dirs, files in os.walk(repo_path):
                if '.git' in root:
                    continue
                for file in files:
                    if file.endswith('.py'):
                        python_files.append(os.path.join(root, file))
            
            for file_path in tqdm(python_files[:50], desc="Analyzing complexity"):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        code = f.read()
                        
                    # Calculate cyclomatic complexity
                    complexity_results = cc_visit(code)
                    file_complexity = sum(c.complexity for c in complexity_results)
                    
                    # Calculate maintainability index
                    mi_results = mi_visit(code, multi=True)
                    mi_score = mi_results if isinstance(mi_results, (int, float)) else 0
                    
                    if file_complexity > 10:
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
            )[:10]
            
            logger.info(f"✅ Analyzed {complexity_data['files_analyzed']} files for complexity")
            return complexity_data
            
        except Exception as e:
            logger.error(f"Error analyzing code complexity: {e}")
            return {}

def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description='Analyze Git repository for insights (simplified version)')
    parser.add_argument('--url', required=True, help='Git repository URL')
    parser.add_argument('--max-commits', type=int, default=1000, help='Maximum number of commits to analyze')
    
    args = parser.parse_args()
    
    try:
        # Create analyzer instance
        analyzer = SimpleCodebaseAnalyzer()
        
        # Analyze repository
        results = analyzer.analyze_repository(args.url, args.max_commits)
        
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