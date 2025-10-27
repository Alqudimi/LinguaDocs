# 📚 Documentation Translation System

A professional, production-ready full-stack application that automatically downloads, parses, translates, and rebuilds documentation sites into multilingual static versions for offline access.

## ✨ Features

- **🌐 Multi-Source Fetching**: Download documentation from GitHub repositories or live websites
- **🔍 Smart Parsing**: Extract translatable content while preserving code blocks and technical syntax
- **🤖 AI Translation**: Offline translation using MarianMT models with automatic language detection
- **🎨 Design Preservation**: Maintain original layout, styling, and structure
- **📦 Offline Packages**: Generate downloadable ZIP archives for complete offline access
- **🚀 Real-time Progress**: Live tracking of fetch, parse, translate, and build operations
- **🌍 12+ Languages**: Support for English, Spanish, French, German, Italian, Portuguese, Russian, Chinese, Japanese, Korean, Arabic, and Hindi

## 🏗️ Architecture

### Backend (Python + FastAPI)
```
backend/
├── main.py              # FastAPI application with REST endpoints
└── modules/
    ├── fetcher.py       # Documentation fetching (GitHub & web)
    ├── parser.py        # Content parsing and extraction
    ├── translator.py    # Translation engine (MarianMT)
    └── builder.py       # Static site generation
```

### Frontend (HTML + TailwindCSS + JavaScript)
```
frontend/
├── index.html           # Main application UI
└── static/
    ├── style.css        # Custom styles
    └── app.js           # Application logic
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Internet connection (for fetching documentation and downloading translation models)

### Installation

1. All dependencies are already installed in this Replit environment
2. The server starts automatically via the configured workflow

### Usage

1. **Access the Application**
   - The UI is available at the webview (port 5000)
   - Click on the webview tab to open the interface

2. **Start a Translation Project**
   - Select source type (GitHub Repository or Live Website)
   - Enter the documentation URL
   - Provide a project name
   - Select source and target languages
   - Click "Start Translation Process"

3. **Monitor Progress**
   - Watch real-time progress through the UI
   - See status for each phase: Fetch → Parse → Translate → Build

4. **Download Results**
   - Once complete, download the ZIP package
   - Extract and open `index.html` for offline access

## 📡 API Endpoints

### Core Endpoints

- `POST /api/fetch` - Fetch documentation from GitHub or website
- `POST /api/parse` - Parse fetched documentation
- `POST /api/translate` - Translate parsed content
- `POST /api/build` - Build static multilingual site
- `GET /api/status/{project_id}` - Get project status
- `GET /api/languages` - List supported languages
- `GET /api/download/{filename}` - Download generated package

### Example API Usage

```bash
# Fetch documentation
curl -X POST http://localhost:5000/api/fetch \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com/user/repo",
    "source_type": "github",
    "max_pages": 50
  }'

# Translate (using project_id from fetch response)
curl -X POST http://localhost:5000/api/translate \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "repo_abc123",
    "source_lang": "en",
    "target_lang": "es"
  }'

# Build static site
curl -X POST http://localhost:5000/api/build \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "repo_abc123",
    "project_name": "my-docs",
    "create_package": true
  }'
```

## 🛠️ Technical Stack

- **Backend**: FastAPI, Uvicorn
- **Translation**: Transformers (MarianMT), SentencePiece
- **Fetching**: aiohttp, requests, GitPython, BeautifulSoup4
- **Parsing**: python-frontmatter, markdown, lxml
- **Templating**: Jinja2
- **Frontend**: TailwindCSS, Vanilla JavaScript

## 📁 Output Structure

Generated sites follow this structure:
```
output/sites/{project_name}/{language}/
├── index.html           # Main index page
├── page1.html          # Translated documentation pages
├── page2.html
└── assets/
    └── style.css       # Styling
```

## 🔧 Configuration

The system uses sensible defaults but can be customized:

- **Max Pages**: Limit website crawling (default: 50 pages)
- **Translation Batch Size**: Process translations in batches (default: 8)
- **Output Directory**: Change where files are saved (default: `output/`)

## 🌟 Use Cases

1. **Open Source Projects**: Translate documentation for international contributors
2. **Developer Tools**: Make technical documentation accessible in multiple languages
3. **Education**: Create multilingual learning resources
4. **Enterprise**: Localize internal documentation for global teams

## 🔐 Security Notes

- GitHub repositories are cloned locally (ensure adequate disk space)
- Translation models are downloaded on first use (~300MB per language pair)
- All processing happens locally - no external API calls for translation

## 🐛 Troubleshooting

### Server won't start
- Check that port 5000 is available
- Verify all Python dependencies are installed

### Translation is slow
- First translation downloads the model (~300MB)
- Subsequent translations use cached models
- Large documentation sets may take several minutes

### Website crawling incomplete
- Increase `max_pages` parameter
- Some sites may have anti-scraping measures
- Consider using the GitHub repository option instead

## 📝 Future Enhancements

- CLI tool for terminal-based usage
- Service worker for browser offline support
- Additional translation models (NLLB, Qwen)
- MkDocs and Docusaurus theme preservation
- Translation memory/cache system
- Custom glossary support for technical terms
- Batch processing for multiple projects

## 📄 License

Open-source ready. Perfect for community use and contributions.

## 🤝 Contributing

This is a production-ready system designed for easy extension:
1. Add new translation backends in `translator.py`
2. Support additional documentation formats in `parser.py`
3. Create custom templates in `backend/templates/`
4. Enhance the UI in `frontend/`

## 💡 Credits

Built with FastAPI, Transformers, and TailwindCSS for a modern, efficient documentation translation experience.
