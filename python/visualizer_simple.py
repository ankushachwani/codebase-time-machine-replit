#!/usr/bin/env python3

import os
import sys
import json
import argparse
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# Import required libraries
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import pandas as pd
    import numpy as np
    from collections import defaultdict, Counter
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.utils import PlotlyJSONEncoder
    import plotly.io as pio
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    print("Please run: pip install matplotlib plotly pandas numpy")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleRepositoryVisualizer:
    """Generate visualizations for repository analysis data without heavy ML dependencies."""
    
    def __init__(self):
        self.analysis_data = {}
        
    def load_analysis_data(self, repo_id: str) -> bool:
        """Load previously analyzed repository data."""
        try:
            analysis_dir = os.path.join(os.getcwd(), 'analysis_data')
            analysis_file = os.path.join(analysis_dir, f"{repo_id}_analysis.json")
            
            if not os.path.exists(analysis_file):
                logger.error(f"Analysis file not found: {analysis_file}")
                return False
                
            with open(analysis_file, 'r') as f:
                self.analysis_data = json.load(f)
                
            logger.info(f"✅ Loaded analysis data for {repo_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading analysis data: {e}")
            return False
    
    def create_commit_activity_timeline(self) -> Dict[str, Any]:
        """Create a timeline visualization showing individual commits as bars."""
        try:
            if not self.analysis_data.get('commits_data'):
                return {'error': 'No commits data available'}
            
            commits = self.analysis_data['commits_data']
            
            # Prepare data for individual commits
            commit_data = []
            for i, commit in enumerate(commits):
                try:
                    commit_date = datetime.fromisoformat(commit['date'].replace('Z', '+00:00'))
                    commit_data.append({
                        'date': commit_date,
                        'date_str': commit_date.strftime('%Y-%m-%d'),
                        'author': commit['author'],
                        'message': commit['message'][:50] + ('...' if len(commit['message']) > 50 else ''),
                        'files_changed': commit.get('files_modified', 0),
                        'commit_index': i + 1
                    })
                except Exception as e:
                    logger.warning(f"Error parsing commit date: {e}")
                    continue
            
            if not commit_data:
                return {'error': 'No valid commit data found'}
            
            # Sort by date
            commit_data = sorted(commit_data, key=lambda x: x['date'])
            
            # Create bar chart with individual commits
            dates = [c['date_str'] for c in commit_data]
            commit_heights = [1] * len(commit_data)  # Each commit is height 1
            authors = [c['author'] for c in commit_data]
            messages = [c['message'] for c in commit_data]
            files_changed = [c['files_changed'] for c in commit_data]
            
            # Create Plotly bar chart
            fig = go.Figure()
            
            # Add bars for each commit
            fig.add_trace(go.Bar(
                x=dates,
                y=commit_heights,
                text=messages,
                hovertemplate='<b>%{text}</b><br>' +
                             'Date: %{x}<br>' +
                             'Author: %{customdata[0]}<br>' +
                             'Files Changed: %{customdata[1]}<br>' +
                             '<extra></extra>',
                customdata=list(zip(authors, files_changed)),
                marker=dict(
                    color=list(range(len(commit_data))),
                    colorscale='Viridis',
                    colorbar=dict(title="Commit Order")
                ),
                name='Commits'
            ))
            
            fig.update_layout(
                title='Repository Commit Activity Timeline',
                xaxis_title="Date",
                yaxis_title="Commits",
                hovermode='x unified',
                template='plotly_white',
                showlegend=False,
                yaxis=dict(
                    tickmode='linear',
                    tick0=0,
                    dtick=1,
                    range=[0, max(2, len(commit_data) * 0.2)]
                )
            )
            
            # Convert to JSON
            plot_json = json.loads(pio.to_json(fig))
            
            return {
                'type': 'commit_timeline',
                'title': 'Commit Activity Timeline',
                'plot': plot_json,
                'summary': {
                    'total_commits': len(commits),
                    'date_range': f"{commit_data[0]['date_str']} to {commit_data[-1]['date_str']}",
                    'most_recent_commit': commit_data[-1]['date_str'],
                    'commits_shown': len(commit_data),
                    'timeline_span_days': (commit_data[-1]['date'] - commit_data[0]['date']).days if len(commit_data) > 1 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating commit timeline: {e}")
            return {'error': str(e)}
    
    def create_author_contribution_chart(self) -> Dict[str, Any]:
        """Create a chart showing author contributions."""
        try:
            if not self.analysis_data.get('insights', {}).get('top_contributors'):
                return {'error': 'No contributor data available'}
            
            contributors = self.analysis_data['insights']['top_contributors']
            
            # Prepare data
            authors = [c['author'] for c in contributors]
            commits = [c['commits'] for c in contributors]
            
            # Create Plotly bar chart
            fig = px.bar(x=commits, y=authors, orientation='h',
                        title='Top Contributors by Commit Count',
                        labels={'x': 'Number of Commits', 'y': 'Author'})
            
            fig.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                template='plotly_white',
                height=max(400, len(authors) * 40)
            )
            
            plot_json = json.loads(pio.to_json(fig))
            
            return {
                'type': 'author_contributions',
                'title': 'Author Contributions',
                'plot': plot_json,
                'summary': {
                    'total_authors': len(authors),
                    'top_contributor': authors[-1] if authors else 'N/A',
                    'top_contributor_commits': commits[-1] if commits else 0,
                    'contribution_distribution': 'See chart for detailed breakdown'
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating author contribution chart: {e}")
            return {'error': str(e)}
    
    def create_file_modification_heatmap(self) -> Dict[str, Any]:
        """Create a heatmap showing file modification patterns."""
        try:
            if not self.analysis_data.get('insights', {}).get('most_modified_files'):
                return {'error': 'No file modification data available'}
            
            modified_files = self.analysis_data['insights']['most_modified_files']
            
            # Prepare data
            files = [f['file'] for f in modified_files[:15]]  # Top 15 files
            modifications = [f['modifications'] for f in modified_files[:15]]
            
            # Create horizontal bar chart
            fig = px.bar(x=modifications, y=files, orientation='h',
                        title='Most Frequently Modified Files',
                        labels={'x': 'Number of Modifications', 'y': 'File Path'},
                        color=modifications,
                        color_continuous_scale='Viridis')
            
            fig.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                template='plotly_white',
                height=max(400, len(files) * 25),
                showlegend=False
            )
            
            plot_json = json.loads(pio.to_json(fig))
            
            return {
                'type': 'file_modifications',
                'title': 'File Modification Frequency',
                'plot': plot_json,
                'summary': {
                    'most_modified_file': files[-1] if files else 'N/A',
                    'total_unique_files': len(modified_files),
                    'modification_range': f"{min(modifications)} to {max(modifications)}" if modifications else 'N/A'
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating file modification heatmap: {e}")
            return {'error': str(e)}
    
    def create_repository_overview(self) -> Dict[str, Any]:
        """Create an overview dashboard with key metrics."""
        try:
            structure = self.analysis_data.get('structure_info', {})
            insights = self.analysis_data.get('insights', {})
            
            # Create a multi-metric overview
            metrics = {
                'Total Commits': structure.get('total_commits', 0),
                'Contributors': structure.get('contributors_count', 0),
                'Files': structure.get('total_files', 0),
                'Lines of Code': structure.get('total_lines', 0)
            }
            
            # Create pie chart for file extensions
            file_ext = structure.get('file_extensions', {})
            if file_ext:
                fig = px.pie(values=list(file_ext.values()), names=list(file_ext.keys()),
                            title='File Type Distribution')
                fig.update_traces(hole=0.4)
                fig.update_layout(template='plotly_white')
                plot_json = json.loads(pio.to_json(fig))
            else:
                plot_json = None
            
            return {
                'type': 'repository_overview',
                'title': 'Repository Overview',
                'plot': plot_json,
                'metrics': metrics,
                'summary': {
                    'repository_size_mb': round(structure.get('repository_size_mb', 0), 2),
                    'analysis_timestamp': self.analysis_data.get('analysis_timestamp', ''),
                    'status': self.analysis_data.get('status', 'unknown'),
                    'dominant_language': max(file_ext.items(), key=lambda x: x[1])[0] if file_ext else 'Unknown'
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating repository overview: {e}")
            return {'error': str(e)}
    
    def create_complexity_analysis(self) -> Dict[str, Any]:
        """Create a complexity analysis visualization."""
        try:
            insights = self.analysis_data.get('insights', {})
            complexity_data = insights.get('complexity_insights', {})
            
            # Since we don't have actual complexity data in simple mode, create a summary
            if not complexity_data or complexity_data.get('files_analyzed', 0) == 0:
                # Create a simple summary based on available data
                structure = self.analysis_data.get('structure_info', {})
                
                # Estimate complexity based on file types and sizes
                file_ext = structure.get('file_extensions', {})
                total_files = structure.get('total_files', 0)
                total_lines = structure.get('total_lines', 0)
                
                # Create mock complexity metrics
                complexity_metrics = {
                    'Total Files': total_files,
                    'Total Lines': total_lines,
                    'Avg Lines per File': round(total_lines / total_files, 1) if total_files > 0 else 0,
                    'Code Files': sum(count for ext, count in file_ext.items() if ext in ['.js', '.py', '.html', '.css', '.java', '.cpp'])
                }
                
                return {
                    'type': 'complexity_analysis',
                    'title': 'Code Complexity Overview',
                    'plot': None,
                    'metrics': complexity_metrics,
                    'summary': {
                        'complexity_status': 'Analysis completed',
                        'maintainability': 'Good' if total_lines < 10000 else 'Moderate',
                        'files_analyzed': 0,  # Simple mode limitation
                        'note': 'Detailed complexity analysis requires advanced mode'
                    }
                }
            
            return {
                'type': 'complexity_analysis', 
                'title': 'Code Complexity Analysis',
                'error': 'Complexity analysis not available in simple mode'
            }
            
        except Exception as e:
            logger.error(f"Error creating complexity analysis: {e}")
            return {'error': str(e)}
    
    def generate_visualization(self, viz_type: str) -> Dict[str, Any]:
        """Generate a specific type of visualization."""
        try:
            logger.info(f"Generating {viz_type} visualization...")
            
            if viz_type == 'timeline':
                return self.create_commit_activity_timeline()
            elif viz_type == 'contributors':
                return self.create_author_contribution_chart()
            elif viz_type == 'files':
                return self.create_file_modification_heatmap()
            elif viz_type == 'overview':
                return self.create_repository_overview()
            elif viz_type == 'complexity':
                return self.create_complexity_analysis()
            else:
                return {'error': f'Visualization type "{viz_type}" not supported in simple mode. Available: timeline, contributors, files, overview, complexity'}
                
        except Exception as e:
            logger.error(f"Error generating {viz_type} visualization: {e}")
            return {'error': str(e)}

def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description='Generate visualizations for repository analysis (simplified)')
    parser.add_argument('--type', required=True, 
                       choices=['timeline', 'contributors', 'files', 'overview', 'complexity'],
                       help='Type of visualization to generate')
    parser.add_argument('--repo-id', required=True, help='Repository ID from analysis')
    
    args = parser.parse_args()
    
    try:
        # Create visualizer instance
        visualizer = SimpleRepositoryVisualizer()
        
        # Load analysis data
        if not visualizer.load_analysis_data(args.repo_id):
            error_result = {
                'error': f'Could not load analysis data for repository ID: {args.repo_id}',
                'repo_id': args.repo_id,
                'timestamp': datetime.now().isoformat()
            }
            print(json.dumps(error_result, indent=2))
            sys.exit(1)
        
        # Generate visualization
        result = visualizer.generate_visualization(args.type)
        
        # Add metadata
        result['repo_id'] = args.repo_id
        result['generated_at'] = datetime.now().isoformat()
        
        # Output results as JSON
        print(json.dumps(result, indent=2, default=str, cls=PlotlyJSONEncoder))
        
    except Exception as e:
        error_result = {
            'error': str(e),
            'type': args.type,
            'repo_id': args.repo_id,
            'timestamp': datetime.now().isoformat()
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)

if __name__ == '__main__':
    main()