# Codebase Time Machine - Deployment Instructions

## 🌱 Overview

The **Codebase Time Machine** is a full-stack web application that analyzes git repositories using AI and machine learning to provide semantic insights about code evolution, developer contributions, and architectural decisions.

## 🚀 Quick Deployment on Replit

### Step 1: Import Project to Replit

1. **Create a new Repl:**
   - Go to [replit.com](https://replit.com)
   - Click "Create Repl"
   - Select "Import from GitHub" or "Upload folder"

2. **Import Methods:**
   
   **Option A: From GitHub (if available)**
   - Paste the GitHub repository URL
   - Click "Import from GitHub"
   
   **Option B: Upload Project Files**
   - Download all project files as ZIP
   - Select "Upload folder" 
   - Choose the project ZIP file
   - Click "Upload"

3. **Initial Setup:**
   - Replit will automatically detect the project as Node.js
   - The `.replit` configuration file will set up the environment

### Step 2: Install Dependencies

The project will automatically install dependencies when first run, but you can manually install them:

```bash
# Install Node.js dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

Set up the following environment variables in Replit:

1. Click on "Secrets" tab in the left sidebar
2. Add these environment variables:

#### Required Environment Variables

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `NODE_ENV` | Environment mode | `production` |
| `PORT` | Server port (auto-set by Replit) | `3000` |

#### Optional Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MAX_COMMITS` | Maximum commits to analyze | `1000` |
| `UPLOAD_MAX_SIZE` | Max upload file size (MB) | `100` |
| `RATE_LIMIT_REQUESTS` | Rate limit per window | `100` |
| `RATE_LIMIT_WINDOW_MS` | Rate limit window (ms) | `900000` |

### Step 4: Run the Application

1. Click the **"Run"** button in Replit
2. The application will:
   - Install all dependencies
   - Start the Node.js server
   - Initialize Python ML models
   - Open the web interface

3. **Run Command:** `npm start`
   - This runs `node server.js`
   - Server starts on port 3000 (or Replit-assigned port)
   - Serves both API and frontend

## 🔧 Project Structure

```
codebase-time-machine/
├── server.js                 # Main Node.js server
├── package.json              # Node.js dependencies
├── requirements.txt          # Python dependencies
├── .replit                   # Replit configuration
├── replit.nix               # Nix environment setup
├── .gitignore               # Git ignore patterns
├── INSTRUCTIONS.md          # This file
├── CLAUDE.md               # AI assistant context
├── public/                 # Frontend files
│   ├── index.html         # Main web interface
│   └── js/
│       └── app.js         # Frontend JavaScript
├── python/                # Python analysis modules
│   ├── analyze_repo.py    # Repository analysis
│   ├── query_engine.py    # Semantic search
│   ├── visualizer.py      # Data visualization
│   └── analyze_uploaded_repo.py # Upload handler
└── analysis_data/         # Generated analysis data (auto-created)
```

## 🌍 Environment Configuration

### Development vs Production

**Development Mode:**
```bash
NODE_ENV=development
```
- Detailed error messages
- CORS allows localhost
- Verbose logging

**Production Mode:**
```bash
NODE_ENV=production
```
- Minimal error exposure
- CORS restricted to domain
- Optimized performance

### Replit-Specific Settings

Replit automatically configures:
- **Domain:** `https://your-repl-name.your-username.repl.co`
- **Port:** Dynamic port assignment
- **HTTPS:** Automatic SSL certificate
- **Environment:** Linux container with Node.js and Python

## 🔍 Features & Usage

### 1. Repository Analysis

**Analyze Git Repository URL:**
- Enter a public GitHub repository URL
- System clones and analyzes commit history
- Generates semantic embeddings for searchability

**Upload Repository Archive:**
- Upload ZIP file of repository
- Supports both git repositories and source code archives
- Extracts and analyzes code structure

### 2. Natural Language Queries

**Example Queries:**
- "How did authentication evolve?"
- "Who worked on the payment system?"
- "Show me refactoring commits"
- "What are the major architectural changes?"

**Query Types:**
- **Semantic Search:** AI-powered understanding
- **Keyword Search:** Traditional text matching
- **Author Search:** Filter by contributor
- **File Search:** Find commits affecting specific files
- **Time Range:** Filter by date ranges

### 3. Visualizations

**Available Visualizations:**
- **Timeline:** Commit activity over time
- **Contributors:** Developer contribution analysis
- **Files:** Most frequently modified files
- **Complexity:** Code complexity metrics
- **Overview:** Repository summary dashboard

## 🛠️ API Endpoints

### Repository Analysis
- `POST /api/analyze-repo-url` - Analyze repository from URL
- `POST /api/upload-repo` - Upload and analyze repository ZIP

### Querying
- `POST /api/query` - Search repository with natural language

### Visualizations  
- `POST /api/visualize` - Generate specific visualizations

### System
- `GET /api/health` - Health check endpoint

## 🔒 Security Features

- **Rate Limiting:** 100 requests per 15 minutes per IP
- **CORS Protection:** Restricted to allowed domains
- **Input Validation:** All inputs sanitized
- **File Upload Limits:** Maximum 100MB ZIP files
- **Helmet Security:** Standard security headers
- **No Sensitive Data:** No API keys or secrets stored

## 🐛 Troubleshooting

### Common Issues

**1. "Python dependencies not found"**
```bash
# Manually install Python packages
pip install -r requirements.txt
```

**2. "Repository clone failed"**
- Ensure repository URL is public and accessible
- Check repository size (very large repos may timeout)
- Verify internet connection in Replit environment

**3. "Analysis timeout"**
- Large repositories may take 5-10 minutes
- Consider reducing `MAX_COMMITS` environment variable
- Check Replit console for detailed error logs

**4. "Visualization not loading"**
- Ensure repository has been analyzed first
- Check browser console for JavaScript errors
- Try refreshing the page

**5. "Upload failed"**
- Ensure file is ZIP format and under 100MB
- Check that ZIP contains git repository or source code
- Verify file is not corrupted

### Performance Optimization

**For Large Repositories:**
- Set `MAX_COMMITS=500` to limit analysis scope
- Use semantic search instead of processing all commits
- Consider analyzing specific time periods

**Memory Management:**
- Replit provides sufficient memory for most repositories
- Very large repos (50,000+ commits) may need optimization
- Analysis data is cached to improve query performance

### Debugging Steps

1. **Check Replit Console:**
   - View server logs in the console tab
   - Look for Python errors or dependency issues

2. **Test API Endpoints:**
   ```bash
   curl https://your-repl.repl.co/api/health
   ```

3. **Verify File Structure:**
   - Ensure all files are uploaded correctly
   - Check that Python files have execute permissions

4. **Restart Application:**
   - Click Stop, then Run again
   - This reinitializes the Python environment

## 📊 Expected Performance

### Analysis Times

| Repository Size | Expected Time | Memory Usage |
|----------------|---------------|--------------|
| Small (< 100 commits) | 30 seconds | 200MB |
| Medium (100-1000 commits) | 2-5 minutes | 500MB |
| Large (1000-5000 commits) | 5-10 minutes | 1GB |
| Very Large (5000+ commits) | 10-20 minutes | 2GB+ |

### Query Performance

- **Semantic Search:** < 2 seconds
- **Keyword Search:** < 1 second  
- **Visualization Generation:** 3-10 seconds
- **File Upload Processing:** 1-5 minutes

## 🎨 Customization

### Theme Modifications

The application uses the **EarthTone** design theme with:
- **Colors:** Forest greens, earth browns, natural tones
- **Fonts:** Merriweather (serif), Open Sans (sans-serif), Pacifico (cursive)
- **Style:** Organic, nature-inspired design elements

**To customize colors:**
1. Edit CSS variables in `public/index.html`
2. Modify the `:root` section with new color values
3. Colors follow the natural/sustainable theme

### Feature Extensions

**Adding New Query Types:**
1. Modify `python/query_engine.py`
2. Add new search methods
3. Update frontend in `public/js/app.js`

**New Visualization Types:**
1. Extend `python/visualizer.py`
2. Add Plotly chart configurations
3. Update frontend tab system

## 🆘 Support

### Getting Help

1. **Check Console Logs:** Most issues show detailed errors
2. **Review Dependencies:** Ensure all packages are installed
3. **Verify Repository:** Test with smaller, public repositories first
4. **Contact Support:** Use GitHub issues for technical problems

### Common Solutions

- **Restart Repl:** Fixes most environment issues
- **Clear Browser Cache:** Resolves frontend loading problems  
- **Check Repository Access:** Ensure URLs are public and valid
- **Monitor Resource Usage:** Large repositories need more time and memory

## 🚀 Production Deployment

For production deployment beyond Replit:

1. **Environment Setup:**
   - Node.js 16+ with npm
   - Python 3.8+ with pip
   - Git command line tools
   - Sufficient memory (2GB+ recommended)

2. **Process Manager:**
   ```bash
   npm install -g pm2
   pm2 start server.js --name "codebase-time-machine"
   ```

3. **Reverse Proxy:**
   - Configure Nginx or Apache
   - Set up SSL certificates
   - Enable GZIP compression

4. **Database (Optional):**
   - Current version uses file-based storage
   - Can be extended to use PostgreSQL/MongoDB
   - Analysis data stored in `analysis_data/` directory

---

## ✅ Quick Start Checklist

- [ ] Import project to Replit
- [ ] Click "Run" button  
- [ ] Wait for dependencies to install
- [ ] Open web interface
- [ ] Test with sample repository URL
- [ ] Try natural language queries
- [ ] Generate visualizations
- [ ] Review analysis results

**🎉 Success!** Your Codebase Time Machine is now running and ready to analyze repositories!

---

*For technical issues or feature requests, check the repository documentation or create an issue.*
