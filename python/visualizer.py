#!/usr/bin/env python3

import os
import sys
import json
import argparse
import base64
from io import BytesIO
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

# Import required libraries
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import seaborn as sns
    import pandas as pd
    import numpy as np
    from collections import defaultdict, Counter
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.utils import PlotlyJSONEncoder
    import plotly.io as pio
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set style for matplotlib
plt.style.use('seaborn-v0_8' if hasattr(plt.style, 'seaborn-v0_8') else 'default')
sns.set_palette("husl")

class RepositoryVisualizer:
    """Generate visualizations for repository analysis data."""
    
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
        """Create a timeline visualization of commit activity."""
        try:
            if not self.analysis_data.get('commits_data'):
                return {'error': 'No commits data available'}
            
            commits = self.analysis_data['commits_data']
            
            # Prepare data
            dates = []
            authors = []
            for commit in commits:
                try:
                    commit_date = datetime.fromisoformat(commit['date'].replace('Z', '+00:00'))
                    dates.append(commit_date.date())
                    authors.append(commit['author'])
                except:
                    continue
            
            if not dates:
                return {'error': 'No valid dates found in commits'}
            
            # Create DataFrame
            df = pd.DataFrame({'date': dates, 'author': authors})
            df['count'] = 1
            
            # Group by date
            daily_commits = df.groupby('date')['count'].sum().reset_index()
            daily_commits['date'] = pd.to_datetime(daily_commits['date'])
            
            # Create Plotly visualization
            fig = px.line(daily_commits, x='date', y='count', 
                         title='Repository Commit Activity Over Time',
                         labels={'count': 'Number of Commits', 'date': 'Date'})
            
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Commits per Day",
                hovermode='x unified',
                template='plotly_white'
            )
            
            # Convert to JSON
            plot_json = json.loads(pio.to_json(fig))
            
            return {
                'type': 'commit_timeline',
                'title': 'Commit Activity Timeline',
                'plot': plot_json,
                'summary': {
                    'total_commits': len(commits),
                    'date_range': f"{min(dates)} to {max(dates)}",
                    'most_active_day': daily_commits.loc[daily_commits['count'].idxmax(), 'date'].strftime('%Y-%m-%d'),
                    'average_commits_per_day': round(daily_commits['count'].mean(), 2)
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
                height=max(400, len(authors) * 30)
            )
            
            # Add percentage annotations
            total_commits = sum(commits)
            for i, (author, commit_count) in enumerate(zip(authors, commits)):
                percentage = (commit_count / total_commits) * 100
                fig.add_annotation(
                    x=commit_count + max(commits) * 0.01,
                    y=i,
                    text=f"{percentage:.1f}%",
                    showarrow=False,
                    font=dict(size=10)
                )
            
            plot_json = json.loads(pio.to_json(fig))
            
            return {
                'type': 'author_contributions',
                'title': 'Author Contributions',
                'plot': plot_json,
                'summary': {
                    'total_authors': len(authors),
                    'top_contributor': authors[-1],  # Last in ascending order
                    'top_contributor_commits': commits[-1],
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
    
    def create_monthly_activity_chart(self) -> Dict[str, Any]:
        """Create a chart showing monthly commit activity."""
        try:
            if not self.analysis_data.get('insights', {}).get('activity_timeline'):
                return {'error': 'No activity timeline data available'}
            
            timeline = self.analysis_data['insights']['activity_timeline']
            
            # Prepare data
            months = list(timeline.keys())
            commits = list(timeline.values())
            
            if not months:
                return {'error': 'No timeline data available'}
            
            # Create line chart
            fig = px.line(x=months, y=commits,
                         title='Monthly Commit Activity',
                         labels={'x': 'Month', 'y': 'Number of Commits'})
            
            fig.update_traces(mode='lines+markers', line=dict(width=3), marker=dict(size=8))
            fig.update_layout(
                xaxis_title="Month",
                yaxis_title="Commits",
                template='plotly_white',
                hovermode='x unified'
            )
            
            plot_json = json.loads(pio.to_json(fig))
            
            # Calculate trends
            if len(commits) > 1:
                recent_avg = np.mean(commits[-3:]) if len(commits) >= 3 else commits[-1]
                overall_avg = np.mean(commits)
                trend = "increasing" if recent_avg > overall_avg else "decreasing"
            else:
                trend = "stable"
            
            return {
                'type': 'monthly_activity',
                'title': 'Monthly Activity Trends',
                'plot': plot_json,
                'summary': {
                    'active_months': len(months),
                    'peak_month': months[commits.index(max(commits))],
                    'peak_commits': max(commits),
                    'average_monthly_commits': round(np.mean(commits), 2),
                    'trend': trend
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating monthly activity chart: {e}")
            return {'error': str(e)}
    
    def create_complexity_analysis(self) -> Dict[str, Any]:
        """Create visualization for code complexity analysis."""
        try:
            complexity_data = self.analysis_data.get('insights', {}).get('complexity_insights', {})
            
            if not complexity_data or not complexity_data.get('high_complexity_files'):
                return {'error': 'No complexity data available'}
            
            high_complexity = complexity_data['high_complexity_files']
            
            # Prepare data
            files = [f['file'] for f in high_complexity]
            complexities = [f['complexity'] for f in high_complexity]
            
            # Create bar chart
            fig = px.bar(x=complexities, y=files, orientation='h',
                        title='High Complexity Files',
                        labels={'x': 'Cyclomatic Complexity', 'y': 'File'},
                        color=complexities,
                        color_continuous_scale='Reds')
            
            fig.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                template='plotly_white',
                height=max(400, len(files) * 30),
                showlegend=False
            )
            
            # Add complexity thresholds
            fig.add_vline(x=10, line_dash="dash", line_color="orange", 
                         annotation_text="Moderate Risk")
            fig.add_vline(x=20, line_dash="dash", line_color="red", 
                         annotation_text="High Risk")
            
            plot_json = json.loads(pio.to_json(fig))
            
            return {
                'type': 'complexity_analysis',
                'title': 'Code Complexity Analysis',
                'plot': plot_json,
                'summary': {
                    'files_analyzed': complexity_data.get('files_analyzed', 0),
                    'average_complexity': round(complexity_data.get('average_complexity', 0), 2),
                    'high_risk_files': len([f for f in high_complexity if f['complexity'] > 20]),
                    'total_complexity': complexity_data.get('total_complexity', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating complexity analysis: {e}")
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
            
            # Create donut charts for file extensions
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
    
    def create_commit_size_distribution(self) -> Dict[str, Any]:
        """Create visualization showing distribution of commit sizes."""
        try:
            if not self.analysis_data.get('commits_data'):
                return {'error': 'No commits data available'}
            
            commits = self.analysis_data['commits_data']
            
            # Extract commit sizes (insertions + deletions)
            commit_sizes = []
            for commit in commits:
                size = (commit.get('insertions', 0) + commit.get('deletions', 0))
                if size > 0:  # Only include commits with changes
                    commit_sizes.append(size)
            
            if not commit_sizes:
                return {'error': 'No commit size data available'}
            
            # Create histogram
            fig = px.histogram(x=commit_sizes, nbins=30,
                              title='Distribution of Commit Sizes',
                              labels={'x': 'Lines Changed (Insertions + Deletions)', 'y': 'Number of Commits'})
            
            fig.update_layout(
                template='plotly_white',
                bargap=0.1
            )
            
            plot_json = json.loads(pio.to_json(fig))
            
            # Calculate statistics
            mean_size = np.mean(commit_sizes)
            median_size = np.median(commit_sizes)
            max_size = max(commit_sizes)
            
            return {
                'type': 'commit_size_distribution',
                'title': 'Commit Size Distribution',
                'plot': plot_json,
                'summary': {
                    'total_commits_analyzed': len(commit_sizes),
                    'average_commit_size': round(mean_size, 1),
                    'median_commit_size': round(median_size, 1),
                    'largest_commit_size': max_size,
                    'small_commits_percent': round((len([s for s in commit_sizes if s <= 50]) / len(commit_sizes)) * 100, 1)
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating commit size distribution: {e}")
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
            elif viz_type == 'monthly':
                return self.create_monthly_activity_chart()
            elif viz_type == 'complexity':
                return self.create_complexity_analysis()
            elif viz_type == 'overview':
                return self.create_repository_overview()
            elif viz_type == 'commit_sizes':
                return self.create_commit_size_distribution()
            elif viz_type == 'all':
                # Generate all visualizations
                all_viz = {}
                viz_types = ['timeline', 'contributors', 'files', 'monthly', 'complexity', 'overview', 'commit_sizes']
                
                for vtype in viz_types:
                    try:
                        all_viz[vtype] = self.generate_visualization(vtype)
                    except Exception as e:
                        logger.warning(f"Failed to generate {vtype}: {e}")
                        all_viz[vtype] = {'error': str(e)}
                
                return {
                    'type': 'all_visualizations',
                    'title': 'Complete Repository Analysis Dashboard',
                    'visualizations': all_viz,
                    'generated_count': len([v for v in all_viz.values() if 'error' not in v])
                }
            else:
                return {'error': f'Unknown visualization type: {viz_type}'}
                
        except Exception as e:
            logger.error(f"Error generating {viz_type} visualization: {e}")
            return {'error': str(e)}

def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description='Generate visualizations for repository analysis')
    parser.add_argument('--type', required=True, 
                       choices=['timeline', 'contributors', 'files', 'monthly', 'complexity', 'overview', 'commit_sizes', 'all'],
                       help='Type of visualization to generate')
    parser.add_argument('--repo-id', required=True, help='Repository ID from analysis')
    
    args = parser.parse_args()
    
    try:
        # Create visualizer instance
        visualizer = RepositoryVisualizer()
        
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