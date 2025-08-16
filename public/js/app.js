// =====================================================
// ROBUST CODEBASE TIME MACHINE - WITH NULL SAFETY
// =====================================================

class CodebaseTimeMachine {
    constructor() {
        this.analysisData = null;
        this.currentRepoId = null;
        console.log('🚀 CodebaseTimeMachine initialized');
    }

    // Store analysis data globally for access
    storeAnalysisData(data) {
        this.analysisData = data.analysis;
        this.currentRepoId = data.analysis.repo_id;
        
        // Also store globally for other functions
        window.analysisData = data.analysis;
        window.currentAnalysisData = data.analysis;
        window.currentRepoId = data.analysis.repo_id;
        
        console.log('✅ Analysis data stored globally');
    }

    // Safe element access with null checking
    safeGetElement(elementId) {
        const element = document.getElementById(elementId);
        if (!element) {
            console.warn(`⚠️ Element not found: ${elementId}`);
        }
        return element;
    }

    // Show/hide loading states safely
    showLoading(elementId, show) {
        const element = this.safeGetElement(elementId);
        if (element) {
            element.style.display = show ? 'block' : 'none';
        }
    }

    // Display visualization in the correct container
    showVisualization(type, vizData) {
        console.log(`📊 Showing ${type} visualization`);
        
        // Map types to actual container IDs
        const containerMap = {
            'timeline': 'viz-timeline',
            'contributors': 'viz-contributors', 
            'files': 'viz-files',
            'complexity': 'viz-complexity',
            'overview': 'viz-overview'
        };
        
        const containerId = containerMap[type] || `viz-${type}`;
        const container = this.safeGetElement(containerId);
        
        if (!container) {
            console.error(`Container ${containerId} not found`);
            return;
        }

        try {
            if (vizData && vizData.data && window.Plotly) {
                Plotly.newPlot(container, vizData.data, vizData.layout || {});
                console.log(`✅ ${type} visualization displayed`);
            } else {
                container.innerHTML = '<div class="alert">No visualization data available</div>';
            }
        } catch (error) {
            console.error('Visualization error:', error);
            container.innerHTML = '<div class="alert alert-error">Error displaying visualization</div>';
        }
    }

    // Generate visualization
    async generateVisualization(type) {
        console.log(`🎯 Generating ${type} visualization`);
        
        const repoId = this.currentRepoId || window.currentRepoId;
        if (!repoId) {
            alert('❌ Please analyze a repository first');
            return;
        }

        try {
            this.showLoading('viz-loading', true);

            const response = await fetch('/api/visualize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type, repoId })
            });

            const data = await response.json();
            
            if (response.ok && data.success) {
                this.showVisualization(type, data.visualization);
            } else {
                alert(`❌ Visualization failed: ${data.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Visualization error:', error);
            alert(`❌ Network error: ${error.message}`);
        } finally {
            this.showLoading('viz-loading', false);
        }
    }
}

// Initialize the main app
window.app = new CodebaseTimeMachine();

// =====================================================
// REPOSITORY ANALYSIS FUNCTION - WITH NULL SAFETY
// =====================================================
window.analyzeRepositoryBackupEnhanced = async function() {
    console.log('🚀 Starting repository analysis');
    
    const repoUrlElement = document.getElementById('repo-url');
    if (!repoUrlElement) {
        console.error('❌ repo-url element not found');
        alert('Error: Form element not found');
        return;
    }
    
    const repoUrl = repoUrlElement.value.trim();
    if (!repoUrl) {
        alert('Please enter a repository URL');
        return;
    }
    
    try {
        // Show loading state safely
        const loadingDiv = document.getElementById('analysis-loading');
        if (loadingDiv) loadingDiv.style.display = 'block';
        
        const response = await fetch('/api/analyze-repo-url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ repoUrl })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Store analysis data
            window.app.storeAnalysisData(data);
            
            // Display results safely
            const resultsDiv = document.getElementById('analysis-results');
            if (resultsDiv) {
                resultsDiv.style.display = 'block';
                resultsDiv.innerHTML = `
                    <div class="card mt-6">
                        <h3>✅ Analysis Complete!</h3>
                        <p><strong>Repository:</strong> ${data.analysis.repo_url}</p>
                        <p><strong>Total Commits:</strong> ${data.analysis.structure_info.total_commits}</p>
                        <p><strong>Contributors:</strong> ${data.analysis.structure_info.contributors_count}</p>
                        <p><strong>Analysis ID:</strong> ${data.analysis.repo_id}</p>
                        <div class="mt-4">
                            <p><strong>🎨 Ready for queries and visualizations!</strong></p>
                        </div>
                    </div>
                `;
                resultsDiv.scrollIntoView({ behavior: 'smooth' });
            }
            
            alert('✅ Analysis completed! You can now ask questions and generate visualizations.');
        } else {
            alert(`❌ Analysis failed: ${data.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Analysis error:', error);
        alert(`❌ Network error: ${error.message}`);
    } finally {
        const loadingDiv = document.getElementById('analysis-loading');
        if (loadingDiv) loadingDiv.style.display = 'none';
    }
};

// =====================================================
// QUERY FUNCTION - WITH PROPER ANSWER HANDLING
// =====================================================
window.queryRepositoryEnhanced = async function() {
    console.log('🔍 Starting repository query');
    
    const questionElement = document.getElementById('query-input');
    if (!questionElement) {
        console.error('❌ query-input element not found');
        alert('Error: Query form element not found');
        return;
    }
    
    const question = questionElement.value.trim();
    if (!question) {
        alert('Please enter a question');
        return;
    }

    const repoId = window.currentRepoId || window.app?.currentRepoId;
    if (!repoId) {
        alert('Please analyze a repository first');
        return;
    }

    try {
        // Show loading safely
        const loadingDiv = document.getElementById('query-loading');
        if (loadingDiv) loadingDiv.style.display = 'block';

        const response = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: question, repoId })
        });

        const data = await response.json();
        console.log('📝 Query response:', data);

        if (response.ok && data.success && data.answer) {
            // Display results with NO height restrictions and proper answer
            const resultsDiv = document.getElementById('query-results');
            if (resultsDiv) {
                resultsDiv.style.display = 'block';
                resultsDiv.innerHTML = `
                    <div class="card mt-4">
                        <h4>💬 Question:</h4>
                        <p class="mb-4">${question}</p>
                        <h4>🤖 AI Response:</h4>
                        <div class="ai-response" style="background: #f8f9fa; padding: 1rem; border-radius: 4px; white-space: pre-wrap; line-height: 1.6; word-wrap: break-word;">${data.answer}</div>
                    </div>
                `;
                resultsDiv.scrollIntoView({ behavior: 'smooth' });
            }
        } else {
            const errorMsg = data.error || 'No answer received';
            alert(`❌ Query failed: ${errorMsg}`);
            console.error('Query failed:', data);
        }
    } catch (error) {
        console.error('Query error:', error);
        alert(`❌ Network error: ${error.message}`);
    } finally {
        const loadingDiv = document.getElementById('query-loading');
        if (loadingDiv) loadingDiv.style.display = 'none';
    }
};

// =====================================================
// TAB SWITCHING - WITH NULL SAFETY
// =====================================================
window.showTabEnhanced = function(tabName, element) {
    // Hide all sections safely
    ['analysis-section', 'query-section', 'visualization-section'].forEach(id => {
        const section = document.getElementById(id);
        if (section) section.style.display = 'none';
    });
    
    // Show target section safely
    const targetSection = document.getElementById(tabName + '-section');
    if (targetSection) {
        targetSection.style.display = 'block';
    }
    
    // Update tab styles safely
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => tab.classList.remove('active'));
    if (element) element.classList.add('active');
    
    console.log(`🔄 Switched to ${tabName} tab`);
};

// =====================================================
// VISUALIZATION FUNCTIONS
// =====================================================
window.generateVisualization = function(type) {
    console.log(`📊 Generate visualization: ${type}`);
    if (window.app) {
        return window.app.generateVisualization(type);
    } else {
        alert('Application not initialized');
    }
};

console.log('🎉 Robust Codebase Time Machine loaded successfully!');
