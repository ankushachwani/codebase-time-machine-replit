# 🚀 Codebase Time Machine - Replit Deployment

AI-powered repository analysis and visualization tool, optimized for Replit deployment.

## ⚡ Quick Setup

1. **Clone to Replit**: Import this repository to Replit
2. **Set Environment Variables**: 
   - Add your Together AI API key: `TOGETHER_API_KEY=your_key_here`
3. **Run**: Click the "Run" button - that's it!

## 🎯 Features

- 📊 **Repository Analysis**: Analyze GitHub repositories or upload local files
- 🤖 **AI-Powered Queries**: Ask natural language questions about codebases  
- 📈 **Interactive Visualizations**: Generate timeline, contributor, and complexity charts
- 🎨 **Modern UI**: Clean, responsive interface with smooth animations

## 🔧 Getting Your API Key

1. Visit [Together AI](https://api.together.ai/)
2. Sign up for a free account
3. Get your API key from the dashboard
4. Add it to Replit Secrets: `TOGETHER_API_KEY`

## 🚀 Usage

1. **Analyze Repository**: Enter a GitHub URL and click "Analyze Repository"
2. **Ask Questions**: Switch to the Query tab and ask about the codebase
3. **Generate Visualizations**: Use the Visualization tab for charts and graphs

## 📁 Project Structure

```
├── server.js              # Express server
├── package.json            # Dependencies
├── requirements.txt        # Python dependencies
├── public/                 # Frontend files
│   ├── index.html         # Main HTML
│   ├── js/app.js          # Frontend JavaScript
│   └── css/style.css      # Styling
├── python/                 # Python analysis scripts
└── analysis_data/          # Generated analysis files
```

## 🛠️ Technical Details

- **Backend**: Node.js + Express
- **Frontend**: Vanilla JavaScript + HTML5/CSS3
- **AI**: Together AI API (Llama models)
- **Visualizations**: Plotly.js
- **Analysis**: Python with ML libraries

## 📝 Environment Variables

- `TOGETHER_API_KEY`: Your Together AI API key (required)
- `PORT`: Server port (default: 3000)
- `NODE_ENV`: Environment mode

---

Built with ❤️ for seamless repository analysis and AI-powered insights.
