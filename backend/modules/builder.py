import os
import shutil
import json
from pathlib import Path
from jinja2 import Template, Environment, FileSystemLoader
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StaticSiteBuilder:
    """Builds multilingual static documentation sites"""
    
    def __init__(self, output_dir: str = "output", template_dir: Optional[str] = None):
        if template_dir is None:
            resolved_template_dir = Path(__file__).resolve().parent.parent / "templates"
        else:
            resolved_template_dir = Path(template_dir).resolve()
        
        self.output_dir = Path(output_dir).resolve()
        self.template_dir = resolved_template_dir
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.template_dir.mkdir(exist_ok=True, parents=True)
        
        self.env = Environment(loader=FileSystemLoader(str(self.template_dir)))
    
    def build_site(self, project_name: str, translated_documents: List[Dict], 
                   target_lang: str, source_lang: str = "en") -> Dict:
        """
        Build a static site from translated documents
        
        Args:
            project_name: Name of the documentation project
            translated_documents: List of translated document dictionaries
            target_lang: Target language code
            source_lang: Source language code
            
        Returns:
            Dict with build results
        """
        try:
            site_dir = self.output_dir / f"sites/{project_name}/{target_lang}"
            if site_dir.exists():
                shutil.rmtree(site_dir)
            
            site_dir.mkdir(parents=True, exist_ok=True)
            
            pages = []
            for doc in translated_documents:
                if doc.get("status") != "success":
                    continue
                
                translated_content = doc.get("translated_content", {})
                file_path = translated_content.get("file_path", "")
                
                html_content = self._render_document(translated_content, target_lang)
                
                file_name = Path(file_path).stem if file_path else "index"
                output_file = site_dir / f"{file_name}.html"
                output_file.write_text(html_content, encoding='utf-8')
                
                pages.append({
                    "file": str(output_file.relative_to(self.output_dir)),
                    "title": file_name.replace('_', ' ').title()
                })
                
                logger.info(f"Generated: {output_file.name}")
            
            self._create_index_page(site_dir, pages, project_name, target_lang)
            
            self._copy_assets(site_dir)
            
            return {
                "status": "success",
                "project_name": project_name,
                "target_lang": target_lang,
                "site_dir": str(site_dir),
                "pages": pages,
                "total_pages": len(pages)
            }
            
        except Exception as e:
            logger.error(f"Site building error: {e}")
            return {"status": "error", "message": str(e)}
    
    def _render_document(self, translated_content: Dict, target_lang: str) -> str:
        """Render a single document to HTML"""
        try:
            template = self.env.get_template("document.html")
        except:
            template = Template(self._get_default_document_template())
        
        translatable_blocks = translated_content.get("translatable_blocks", [])
        code_blocks = translated_content.get("code_blocks", [])
        metadata = translated_content.get("metadata", {})
        
        content_html = ""
        for block in translatable_blocks:
            text = block.get("translated_content", block.get("content", ""))
            content_html += f"<p>{text}</p>\n"
        
        for code_block in code_blocks:
            code_content = code_block.get("content", "")
            content_html += f'<pre><code>{code_content}</code></pre>\n'
        
        title = metadata.get("title", "Documentation")
        
        return template.render(
            title=title,
            content=content_html,
            language=target_lang,
            metadata=metadata
        )
    
    def _create_index_page(self, site_dir: Path, pages: List[Dict], 
                          project_name: str, language: str):
        """Create an index page linking to all documents"""
        try:
            template = self.env.get_template("index.html")
        except:
            template = Template(self._get_default_index_template())
        
        html = template.render(
            project_name=project_name,
            language=language,
            pages=pages
        )
        
        index_file = site_dir / "index.html"
        index_file.write_text(html, encoding='utf-8')
        logger.info("Created index page")
    
    def _copy_assets(self, site_dir: Path):
        """Copy CSS and other assets to the site directory"""
        assets_dir = site_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        
        css_content = self._get_default_css()
        css_file = assets_dir / "style.css"
        css_file.write_text(css_content)
    
    def _get_default_document_template(self) -> str:
        """Get default document template"""
        return '''<!DOCTYPE html>
<html lang="{{ language }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>{{ title }}</h1>
        </header>
        <main>
            {{ content|safe }}
        </main>
        <footer>
            <a href="index.html">← Back to Index</a>
        </footer>
    </div>
</body>
</html>'''
    
    def _get_default_index_template(self) -> str:
        """Get default index template"""
        return '''<!DOCTYPE html>
<html lang="{{ language }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ project_name }} Documentation</title>
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>{{ project_name }}</h1>
            <p class="subtitle">Documentation ({{ language }})</p>
        </header>
        <main>
            <h2>Table of Contents</h2>
            <ul class="page-list">
            {% for page in pages %}
                <li><a href="{{ page.file.split('/')[-1] }}">{{ page.title }}</a></li>
            {% endfor %}
            </ul>
        </main>
    </div>
</body>
</html>'''
    
    def _get_default_css(self) -> str:
        """Get default CSS styling"""
        return '''* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.6;
    color: #333;
    background: #f5f5f5;
}

.container {
    max-width: 900px;
    margin: 0 auto;
    padding: 2rem;
    background: white;
    min-height: 100vh;
    box-shadow: 0 0 10px rgba(0,0,0,0.1);
}

header {
    border-bottom: 3px solid #4a90e2;
    padding-bottom: 1.5rem;
    margin-bottom: 2rem;
}

h1 {
    color: #2c3e50;
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
}

h2 {
    color: #34495e;
    margin-top: 2rem;
    margin-bottom: 1rem;
    font-size: 1.8rem;
}

.subtitle {
    color: #7f8c8d;
    font-size: 1.1rem;
}

p {
    margin-bottom: 1rem;
    line-height: 1.8;
}

.page-list {
    list-style: none;
    padding: 0;
}

.page-list li {
    margin-bottom: 0.8rem;
}

.page-list a {
    color: #4a90e2;
    text-decoration: none;
    font-size: 1.1rem;
    padding: 0.5rem;
    display: block;
    border-left: 3px solid transparent;
    transition: all 0.3s;
}

.page-list a:hover {
    border-left-color: #4a90e2;
    background: #f8f9fa;
    padding-left: 1rem;
}

pre {
    background: #282c34;
    color: #abb2bf;
    padding: 1rem;
    border-radius: 5px;
    overflow-x: auto;
    margin: 1rem 0;
}

code {
    font-family: 'Courier New', monospace;
    font-size: 0.9rem;
}

footer {
    margin-top: 3rem;
    padding-top: 2rem;
    border-top: 1px solid #e1e4e8;
}

footer a {
    color: #4a90e2;
    text-decoration: none;
}

footer a:hover {
    text-decoration: underline;
}
'''
    
    def create_downloadable_package(self, site_dir: str, project_name: str, 
                                   language: str) -> Dict:
        """
        Create a ZIP archive of the generated site
        
        Args:
            site_dir: Directory containing the built site
            project_name: Name of the project
            language: Language code
            
        Returns:
            Dict with package information
        """
        try:
            import zipfile
            
            downloads_dir = Path("downloads")
            downloads_dir.mkdir(exist_ok=True)
            
            zip_name = f"{project_name}_{language}_docs.zip"
            zip_path = downloads_dir / zip_name
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                site_path = Path(site_dir)
                for file_path in site_path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(site_path.parent)
                        zipf.write(file_path, arcname)
            
            file_size = zip_path.stat().st_size
            
            logger.info(f"Created package: {zip_name}")
            
            return {
                "status": "success",
                "zip_name": zip_name,
                "zip_path": str(zip_path),
                "size_bytes": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"Package creation error: {e}")
            return {"status": "error", "message": str(e)}
