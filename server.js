const express = require('express');
const cors = require('cors');
const path = require('path');
const multer = require('multer');
const { spawn } = require('child_process');
const fs = require('fs');
require('dotenv').config();
const compression = require('compression');
const morgan = require('morgan');

const app = express();
const PORT = process.env.PORT || 4000;

// Security and performance middleware

app.use(compression());
app.use(morgan('combined'));

// Rate limiting

// CORS and body parsing
app.use(cors({
  origin: true,
  credentials: true,
  methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization", "Accept"]
}));

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Serve static files
app.use(express.static(path.join(__dirname, 'public')));

// Create uploads directory if it doesn't exist
const uploadsDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, uploadsDir);
  },
  filename: (req, file, cb) => {
    const timestamp = Date.now();
    cb(null, `repo-${timestamp}-${file.originalname}`);
  }
});

const upload = multer({ 
  storage: storage,
  limits: {
    fileSize: 100 * 1024 * 1024 // 100MB limit
  },
  fileFilter: (req, file, cb) => {
    // Allow zip files and common archive formats
    if (file.mimetype === 'application/zip' || 
        file.mimetype === 'application/x-zip-compressed' ||
        file.originalname.endsWith('.zip')) {
      cb(null, true);
    } else {
      cb(new Error('Only ZIP files are allowed'));
    }
  }
});

// API Routes

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

// Analyze repository from URL
app.post('/api/analyze-repo-url', async (req, res) => {
  try {
    const { repoUrl } = req.body;
    
    if (!repoUrl) {
      return res.status(400).json({ error: 'Repository URL is required' });
    }

    // Validate URL format
    const urlPattern = /^https?:\/\/.+\/.+\.git$|^https?:\/\/.+\/.+$/;
    if (!urlPattern.test(repoUrl)) {
      return res.status(400).json({ error: 'Invalid repository URL format' });
    }

    console.log(`Starting analysis for repo: ${repoUrl}`);
    
    // Call Python script for analysis (use simple version for compatibility)
    const pythonProcess = spawn('python3', [
      path.join(__dirname, 'python', 'analyze_repo_simple.py'),
      '--url', repoUrl,
      '--max-commits', process.env.MAX_COMMITS || '500'
    ]);

    let output = '';
    let error = '';

    pythonProcess.stdout.on('data', (data) => {
      output += data.toString();
      console.log('Python output:', data.toString());
    });

    pythonProcess.stderr.on('data', (data) => {
      error += data.toString();
      console.error('Python error:', data.toString());
    });

    pythonProcess.on('close', (code) => {
      if (code === 0) {
        try {
          const result = JSON.parse(output);
          res.json({ 
            success: true, 
            analysis: result,
            repoUrl: repoUrl
          });
        } catch (parseError) {
          console.error('Error parsing Python output:', parseError);
          res.status(500).json({ 
            error: 'Error parsing analysis results',
            details: output
          });
        }
      } else {
        console.error(`Python process exited with code ${code}`);
        res.status(500).json({ 
          error: 'Analysis failed',
          details: error || 'Unknown error occurred'
        });
      }
    });

    pythonProcess.on('error', (err) => {
      console.error('Failed to start Python process:', err);
      res.status(500).json({ 
        error: 'Failed to start analysis process',
        details: err.message
      });
    });

  } catch (error) {
    console.error('Error in analyze-repo-url:', error);
    res.status(500).json({ 
      error: 'Internal server error',
      details: error.message
    });
  }
});

// Query repository analysis
// Query repository analysis
app.post('/api/query', async (req, res) => {
  try {
    const { query, repoId } = req.body;
    
    if (!query) {
      return res.status(400).json({ error: 'Query is required' });
    }

    console.log(`Processing query: ${query}`);
    
    // Call Python script for querying (use simple version)
    const pythonProcess = spawn('python3', [
      path.join(__dirname, 'python', 'query_engine_simple.py'),
      '--query', query,
      '--repo-id', repoId || 'default'
    ]);

    let pythonOutput = '';
    let pythonError = '';

    pythonProcess.stdout.on('data', (data) => {
      pythonOutput += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      pythonError += data.toString();
      console.log('Query error:', data.toString());
    });

    pythonProcess.on('close', (code) => {
      try {
        if (pythonError) {
          console.log('Python stderr:', pythonError);
        }
        
        if (code !== 0) {
          console.error(`Python script exited with code ${code}`);
          return res.status(500).json({ 
            success: false, 
            error: 'Query processing failed',
            details: pythonError
          });
        }

        // Parse Python output
        let result;
        try {
          result = JSON.parse(pythonOutput);
        } catch (parseError) {
          console.error('Failed to parse Python output:', parseError);
          console.error('Raw output:', pythonOutput);
          return res.status(500).json({ 
            success: false, 
            error: 'Invalid response from query engine',
            raw_output: pythonOutput.substring(0, 500)
          });
        }

        // Check if the Python script returned an error
        if (result.error) {
          return res.json({
            success: false,
            error: result.error,
            suggestions: result.suggestions || []
          });
        }

        // Success case - return the answer
        if (result.success && result.answer) {
          return res.json({
            success: true,
            answer: result.answer,
            query: query,
            repo_id: repoId
          });
        } else {
          // Handle case where success=true but no answer
          return res.json({
            success: false,
            error: 'No answer received from AI',
            debug_result: result
          });
        }

      } catch (error) {
        console.error('Error processing Python response:', error);
        return res.status(500).json({ 
          success: false, 
          error: 'Error processing query response',
          details: error.message
        });
      }
    });

  } catch (error) {
    console.error('Query endpoint error:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Server error processing query',
      details: error.message
    });
  }
});

// Generate visualizations
app.post('/api/visualize', async (req, res) => {
  try {
    const { type, repoId } = req.body;
    
    if (!type) {
      return res.status(400).json({ error: 'Visualization type is required' });
    }

    console.log(`Generating ${type} visualization`);
    
    // Call Python script for visualization (use simple version)
    const pythonProcess = spawn('python3', [
      path.join(__dirname, 'python', 'visualizer_simple.py'),
      '--type', type,
      '--repo-id', repoId || 'default'
    ]);

    let output = '';
    let error = '';

    pythonProcess.stdout.on('data', (data) => {
      output += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      error += data.toString();
      console.error('Visualization error:', data.toString());
    });

    pythonProcess.on('close', (code) => {
      if (code === 0) {
        try {
          const result = JSON.parse(output);
          res.json({ 
            success: true, 
            visualization: result,
            type: type
          });
        } catch (parseError) {
          res.status(500).json({ 
            error: 'Error parsing visualization results',
            details: output
          });
        }
      } else {
        res.status(500).json({ 
          error: 'Visualization generation failed',
          details: error || 'Unknown error occurred'
        });
      }
    });

  } catch (error) {
    console.error('Error in visualize:', error);
    res.status(500).json({ 
      error: 'Internal server error',
      details: error.message
    });
  }
});

// Upload and analyze repository zip file
app.post('/api/upload-repo', upload.single('repoFile'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    const filePath = req.file.path;
    console.log(`Processing uploaded file: ${filePath}`);
    
    // Call Python script for ZIP analysis
    const pythonProcess = spawn('python3', [
      path.join(__dirname, 'python', 'analyze_uploaded_repo.py'),
      '--file', filePath
    ]);

    let output = '';
    let error = '';

    pythonProcess.stdout.on('data', (data) => {
      output += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      error += data.toString();
      console.error('Upload analysis error:', data.toString());
    });

    pythonProcess.on('close', (code) => {
      // Clean up uploaded file
      fs.unlink(filePath, (err) => {
        if (err) console.error('Error deleting uploaded file:', err);
      });

      if (code === 0) {
        try {
          const result = JSON.parse(output);
          res.json({ 
            success: true, 
            analysis: result,
            filename: req.file.originalname
          });
        } catch (parseError) {
          res.status(500).json({ 
            error: 'Error parsing analysis results',
            details: output
          });
        }
      } else {
        res.status(500).json({ 
          error: 'Analysis failed',
          details: error || 'Unknown error occurred'
        });
      }
    });

  } catch (error) {
    console.error('Error in upload-repo:', error);
    res.status(500).json({ 
      error: 'Internal server error',
      details: error.message
    });
  }
});

// Error handling middleware
app.use((error, req, res, next) => {
  if (error instanceof multer.MulterError) {
    if (error.code === 'LIMIT_FILE_SIZE') {
      return res.status(400).json({ error: 'File too large. Maximum size is 100MB.' });
    }
  }
  
  console.error('Unhandled error:', error);
  res.status(500).json({ 
    error: 'Internal server error',
    details: process.env.NODE_ENV === 'development' ? error.message : 'Something went wrong'
  });
});

// Serve the main application
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Start server
const server = app.listen(PORT, '0.0.0.0', () => {
  console.log(`🌱 Codebase Time Machine server running on port ${PORT}`);
  console.log(`🌍 Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`☁️  Deployment: AWS optimized`);
  console.log(`🚀 Ready for repository analysis!`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('SIGINT received, shutting down gracefully');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

module.exports = app;