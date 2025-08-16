#!/usr/bin/env python3

import os
import sys
import json
import argparse
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import re
from together import Together
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CodebaseQueryEngine:
    def __init__(self):
        self.api_key = os.getenv("TOGETHER_API_KEY")
        if not self.api_key:
            raise ValueError("TOGETHER_API_KEY environment variable is required")
        
        logger.info(f"API Key found: {bool(self.api_key)}")
        
        try:
            self.client = Together(api_key=self.api_key)
            logger.info("✅ Together AI client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Together AI client: {e}")
            raise

    def load_analysis_data(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """Load analysis data from JSON file."""
        # Use absolute path from the main project directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        analysis_file = os.path.join(base_dir, 'analysis_data', f'{repo_id}_analysis.json')
        
        logger.info(f"Looking for analysis file: {analysis_file}")
        
        if not os.path.exists(analysis_file):
            logger.error(f"Analysis file not found: {analysis_file}")
            return None
        
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"✅ Loaded analysis data for {repo_id}")
            return data
        except Exception as e:
            logger.error(f"❌ Error loading analysis data: {e}")
            return None

    def create_context_from_analysis(self, analysis_data: Dict[str, Any]) -> str:
        """Create a comprehensive context string from analysis data."""
        try:
            context_parts = []
            
            # Repository basic info
            if 'repo_url' in analysis_data:
                context_parts.append(f"Repository: {analysis_data['repo_url']}")
            
            # Structure information
            if 'structure_info' in analysis_data:
                structure = analysis_data['structure_info']
                context_parts.append(f"Total commits: {structure.get('total_commits', 'N/A')}")
                context_parts.append(f"Contributors: {structure.get('contributors_count', 'N/A')}")
                context_parts.append(f"Total files: {structure.get('total_files', 'N/A')}")
                context_parts.append(f"Repository size: {structure.get('repository_size_mb', 'N/A')} MB")
                context_parts.append(f"Total branches: {structure.get('total_branches', 'N/A')}")
            
            # Recent commits info
            if 'commit_analysis' in analysis_data and 'recent_commits' in analysis_data['commit_analysis']:
                recent_commits = analysis_data['commit_analysis']['recent_commits']
                if recent_commits:
                    context_parts.append("\nRecent commits:")
                    for commit in recent_commits[:5]:  # Last 5 commits
                        commit_info = f"- {commit.get('date', 'N/A')}: {commit.get('message', 'N/A')[:100]}"
                        if commit.get('author'):
                            commit_info += f" (by {commit['author']})"
                        context_parts.append(commit_info)
            
            # File structure
            if 'file_analysis' in analysis_data and 'file_types' in analysis_data['file_analysis']:
                file_types = analysis_data['file_analysis']['file_types']
                if file_types:
                    context_parts.append("\nFile types in repository:")
                    for file_type, count in list(file_types.items())[:10]:  # Top 10 file types
                        context_parts.append(f"- {file_type}: {count} files")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"❌ Error creating context: {e}")
            return "Error processing repository analysis data."

    def query_repository(self, query: str, repo_id: str) -> Dict[str, Any]:
        """Query the repository using Together AI."""
        try:
            # Load analysis data
            analysis_data = self.load_analysis_data(repo_id)
            if not analysis_data:
                return {
                    "error": f"Repository analysis not found for ID: {repo_id}",
                    "suggestions": [
                        "Please analyze the repository first",
                        "Check if the repository ID is correct"
                    ]
                }
            
            # Create context
            context = self.create_context_from_analysis(analysis_data)
            
            # Create prompt for Together AI
            prompt = f"""You are an expert code repository analyst. Based on the following repository analysis, please answer the user's question comprehensively and accurately.

Repository Analysis Context:
{context}

User Question: {query}

Please provide a detailed, informative answer based on the repository data above. If the question cannot be fully answered with the available data, explain what information is available and suggest what additional analysis might be helpful."""

            logger.info(f"🤖 Sending query to Together AI: {query[:50]}...")
            
            # Query Together AI
            response = self.client.completions.create(
                model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
                prompt=prompt,
                max_tokens=1000,
                temperature=0.7,
                top_p=0.9,
                stop=["<|im_end|>"]
            )
            
            if response.choices and len(response.choices) > 0:
                answer = response.choices[0].text.strip()
                logger.info("✅ Successfully received response from Together AI")
                
                return {
                    "success": True,
                    "answer": answer,
                    "query": query,
                    "repo_id": repo_id
                }
            else:
                logger.error("❌ No response received from Together AI")
                return {
                    "error": "No response received from AI service",
                    "query": query
                }
                
        except Exception as e:
            logger.error(f"❌ Query processing error: {e}")
            return {
                "error": f"Error processing query: {str(e)}",
                "query": query
            }

def main():
    parser = argparse.ArgumentParser(description='Query repository analysis using AI')
    parser.add_argument('--query', required=True, help='Query to ask about the repository')
    parser.add_argument('--repo-id', required=True, help='Repository ID for analysis data')
    
    args = parser.parse_args()
    
    try:
        # Initialize query engine
        query_engine = CodebaseQueryEngine()
        
        # Process query
        result = query_engine.query_repository(args.query, args.repo_id)
        
        # Output result as JSON
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        error_result = {
            "error": f"Failed to initialize query engine: {str(e)}",
            "query": args.query
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()
