#!/usr/bin/env python3

import os
import sys
import json
import argparse
import tempfile
import shutil
import zipfile
from datetime import datetime
import logging

# Import the simple analyzer
try:
    from analyze_repo_simple import SimpleCodebaseAnalyzer
except ImportError:
    # Add current directory to path for imports
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from analyze_repo_simple import SimpleCodebaseAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UploadedRepoAnalyzer:
    """Analyzer for uploaded repository zip files."""
    
    def __init__(self):
        self.analyzer = SimpleCodebaseAnalyzer()
    
    def extract_zip_file(self, zip_path: str) -> str:
        """Extract uploaded zip file to temporary directory."""
        try:
            logger.info(f"Extracting zip file: {zip_path}")
            
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix="ctm_upload_")
            
            # Extract zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Find the actual repository directory (might be nested)
            extracted_items = os.listdir(temp_dir)
            
            if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_dir, extracted_items[0])):
                # Single directory extracted, use that as repo path
                repo_path = os.path.join(temp_dir, extracted_items[0])
            else:
                # Multiple items or files, use temp_dir as repo path
                repo_path = temp_dir
            
            # Verify it's a git repository
            if not os.path.exists(os.path.join(repo_path, '.git')):
                logger.warning(f"No .git directory found in {repo_path}")
                # Still proceed as it might be a source code archive without git
            
            logger.info(f"✅ Extracted to: {repo_path}")
            return repo_path
            
        except Exception as e:
            logger.error(f"Error extracting zip file: {e}")
            raise
    
    def analyze_uploaded_repository(self, zip_path: str) -> dict:
        """Analyze an uploaded repository zip file."""
        temp_dir = None
        try:
            # Extract zip file
            repo_path = self.extract_zip_file(zip_path)
            temp_dir = repo_path
            
            # Check if it's a git repository
            if os.path.exists(os.path.join(repo_path, '.git')):
                logger.info("Git repository detected, performing full analysis...")
                
                # Analyze repository structure
                structure_info = self.analyzer.analyze_repository_structure(repo_path)
                
                # Extract commits data using pydriller
                commits_data = self.analyzer.extract_commits_data(repo_path)
                
            else:
                logger.info("No git repository detected, performing structure analysis only...")
                
                # Basic structure analysis for non-git archives
                structure_info = self.analyze_source_structure(repo_path)
                commits_data = self.create_synthetic_commits(repo_path, structure_info)
            
            # Extract actual code content for AI analysis
            code_content = self.analyzer.extract_code_content(repo_path)
            
            # Generate insights
            insights = self.generate_upload_insights(structure_info, commits_data)
            
            # Generate repo ID based on content
            repo_id = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Prepare analysis results
            analysis_results = {
                'repo_id': repo_id,
                'repo_source': 'uploaded_file',
                'original_filename': os.path.basename(zip_path),
                'analysis_timestamp': datetime.now().isoformat(),
                'structure_info': structure_info,
                'commits_data': commits_data,
                'code_content': code_content,
                'insights': insights,
                'is_git_repo': os.path.exists(os.path.join(repo_path, '.git')),
                'status': 'completed'
            }
            
            # Save results if commits were found
            if commits_data or structure_info:
                self.analyzer.save_analysis_results(repo_id, analysis_results)
            
            # Return clean results (without embeddings)
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
            logger.error(f"Error analyzing uploaded repository: {e}")
            return {
                'error': str(e),
                'status': 'failed',
                'analysis_timestamp': datetime.now().isoformat(),
                'original_filename': os.path.basename(zip_path) if zip_path else 'unknown'
            }
        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    # Get the parent temp directory if we used a subdirectory
                    if temp_dir.endswith(os.listdir(temp_dir.split('/')[:-1])[0]):
                        cleanup_dir = os.path.dirname(temp_dir)
                    else:
                        cleanup_dir = temp_dir
                    
                    shutil.rmtree(cleanup_dir)
                    logger.info(f"Cleaned up temporary directory: {cleanup_dir}")
                except Exception as e:
                    logger.warning(f"Could not clean up temporary directory: {e}")
    
    def analyze_source_structure(self, repo_path: str) -> dict:
        """Analyze source code structure for non-git archives."""
        try:
            logger.info("Analyzing source code structure...")
            
            file_extensions = {}
            total_files = 0
            total_lines = 0
            directories = set()
            
            for root, dirs, files in os.walk(repo_path):
                # Add directories to set
                for d in dirs:
                    directories.add(os.path.relpath(os.path.join(root, d), repo_path))
                
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        # Get file extension
                        ext = os.path.splitext(file)[1].lower()
                        if ext:
                            file_extensions[ext] = file_extensions.get(ext, 0) + 1
                        
                        # Count lines for text files
                        if ext in ['.py', '.js', '.java', '.cpp', '.c', '.h', '.css', '.html', '.md', '.txt', '.json', '.xml']:
                            try:
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    lines = len(f.readlines())
                                    total_lines += lines
                            except:
                                pass
                        
                        total_files += 1
                    except:
                        continue
            
            structure_info = {
                'total_commits': 0,  # No git history
                'total_branches': 0,
                'total_files': total_files,
                'total_lines': total_lines,
                'total_directories': len(directories),
                'file_extensions': dict(sorted(file_extensions.items(), key=lambda x: x[1], reverse=True)[:15]),
                'contributors_count': 0,  # Unknown for source archives
                'repository_size_mb': self.analyzer.get_directory_size(repo_path) / (1024 * 1024)
            }
            
            logger.info(f"Source structure analyzed: {total_files} files, {total_lines} lines")
            return structure_info
            
        except Exception as e:
            logger.error(f"Error analyzing source structure: {e}")
            return {}
    
    def create_synthetic_commits(self, repo_path: str, structure_info: dict) -> list:
        """Create synthetic commit data for non-git local uploads."""
        try:
            commits_data = []
            current_time = datetime.now().isoformat()
            
            # Create a single synthetic commit representing the uploaded code
            file_extensions = structure_info.get('file_extensions', {})
            total_files = structure_info.get('total_files', 0)
            total_lines = structure_info.get('total_lines', 0)
            
            # Determine project type
            primary_language = "Unknown"
            if file_extensions:
                sorted_exts = sorted(file_extensions.items(), key=lambda x: x[1], reverse=True)
                primary_ext = sorted_exts[0][0]
                language_map = {
                    '.py': 'Python', '.js': 'JavaScript', '.java': 'Java',
                    '.cpp': 'C++', '.c': 'C', '.cs': 'C#', '.go': 'Go',
                    '.rb': 'Ruby', '.php': 'PHP', '.ts': 'TypeScript',
                    '.html': 'HTML', '.css': 'CSS', '.sql': 'SQL',
                    '.rs': 'Rust', '.kt': 'Kotlin', '.swift': 'Swift'
                }
                primary_language = language_map.get(primary_ext, primary_ext.replace('.', '').upper())
            
            synthetic_commit = {
                'hash': f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'author': 'Local Upload',
                'author_email': 'local@upload.com',
                'date': current_time,
                'message': f'Uploaded {primary_language} project with {total_files} files ({total_lines} lines of code)',
                'files_modified': total_files,
                'insertions': total_lines,
                'deletions': 0,
                'file_changes': []
            }
            
            # Add representative file changes
            for ext, count in list(file_extensions.items())[:5]:
                synthetic_commit['file_changes'].append({
                    'filename': f"*{ext}",
                    'status': 'added',
                    'insertions': count * 20,  # Estimate lines per file
                    'deletions': 0
                })
            
            commits_data.append(synthetic_commit)
            
            logger.info(f"✅ Created synthetic commit data for local upload")
            return commits_data
            
        except Exception as e:
            logger.error(f"Error creating synthetic commits: {e}")
            return []
    
    def generate_upload_insights(self, structure_info: dict, commits_data: list) -> dict:
        """Generate insights for uploaded repository."""
        try:
            insights = {
                'summary': {
                    'total_commits_analyzed': len(commits_data),
                    'total_files': structure_info.get('total_files', 0),
                    'total_lines': structure_info.get('total_lines', 0),
                    'analysis_type': 'git_repository' if commits_data else 'source_archive'
                }
            }
            
            # File type analysis
            file_extensions = structure_info.get('file_extensions', {})
            if file_extensions:
                insights['file_type_distribution'] = [
                    {'extension': ext, 'count': count} 
                    for ext, count in list(file_extensions.items())[:10]
                ]
                
                # Determine primary language
                primary_ext = max(file_extensions.items(), key=lambda x: x[1])[0]
                language_map = {
                    '.py': 'Python', '.js': 'JavaScript', '.java': 'Java',
                    '.cpp': 'C++', '.c': 'C', '.cs': 'C#', '.go': 'Go',
                    '.rb': 'Ruby', '.php': 'PHP', '.ts': 'TypeScript',
                    '.html': 'HTML', '.css': 'CSS', '.sql': 'SQL'
                }
                insights['primary_language'] = language_map.get(primary_ext, primary_ext)
            
            # Add git-specific insights if available
            if commits_data:
                # Simple insights for uploaded repos
                author_stats = {}
                for commit in commits_data:
                    author = commit['author']
                    author_stats[author] = author_stats.get(author, 0) + 1
                insights['top_contributors'] = [{'author': author, 'commits': count} for author, count in author_stats.items()]
            
            # Add basic file insights
            insights['file_analysis'] = {
                'total_file_types': len(file_extensions),
                'largest_file_type': max(file_extensions.items(), key=lambda x: x[1])[0] if file_extensions else 'none'
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating upload insights: {e}")
            return {'error': str(e)}

def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description='Analyze uploaded repository zip file')
    parser.add_argument('--file', required=True, help='Path to uploaded zip file')
    
    args = parser.parse_args()
    
    try:
        if not os.path.exists(args.file):
            raise FileNotFoundError(f"File not found: {args.file}")
        
        # Create analyzer instance
        analyzer = UploadedRepoAnalyzer()
        
        # Analyze uploaded repository
        results = analyzer.analyze_uploaded_repository(args.file)
        
        # Output results as JSON
        print(json.dumps(results, indent=2, default=str))
        
    except Exception as e:
        error_result = {
            'error': str(e),
            'status': 'failed',
            'analysis_timestamp': datetime.now().isoformat(),
            'file_path': args.file
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)

if __name__ == '__main__':
    main()