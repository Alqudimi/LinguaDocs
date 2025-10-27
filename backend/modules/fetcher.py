import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from git import Repo
import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentationFetcher:
    """Fetches documentation from GitHub repositories or live websites"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
    async def fetch_github_repo(self, repo_url: str, target_path: Optional[str] = None) -> Dict:
        """
        Clone a GitHub repository and extract documentation
        
        Args:
            repo_url: GitHub repository URL
            target_path: Specific path within repo (e.g., 'docs/')
            
        Returns:
            Dict with status and file paths
        """
        try:
            repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
            clone_path = self.output_dir / f"repos/{repo_name}"
            
            if clone_path.exists():
                shutil.rmtree(clone_path)
            
            clone_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Cloning repository: {repo_url}")
            Repo.clone_from(repo_url, str(clone_path))
            
            if target_path:
                docs_path = clone_path / target_path
            else:
                for common_dir in ['docs', 'documentation', 'doc']:
                    potential_path = clone_path / common_dir
                    if potential_path.exists():
                        docs_path = potential_path
                        break
                else:
                    docs_path = clone_path
            
            files = self._collect_documentation_files(docs_path)
            
            return {
                "status": "success",
                "repo_name": repo_name,
                "clone_path": str(clone_path),
                "docs_path": str(docs_path),
                "files": files,
                "file_count": len(files)
            }
            
        except Exception as e:
            logger.error(f"Error fetching GitHub repo: {e}")
            return {"status": "error", "message": str(e)}
    
    async def fetch_website(self, url: str, max_pages: int = 50) -> Dict:
        """
        Fetch documentation from a live website
        
        Args:
            url: Base URL of the documentation site
            max_pages: Maximum number of pages to crawl
            
        Returns:
            Dict with status and downloaded pages
        """
        try:
            domain = url.split('/')[2]
            site_name = domain.replace('.', '_')
            site_path = self.output_dir / f"sites/{site_name}"
            site_path.mkdir(parents=True, exist_ok=True)
            
            visited_urls = set()
            pages = []
            
            async with aiohttp.ClientSession() as session:
                await self._crawl_page(session, url, url, visited_urls, pages, max_pages, site_path)
            
            return {
                "status": "success",
                "site_name": site_name,
                "site_path": str(site_path),
                "pages": pages,
                "page_count": len(pages)
            }
            
        except Exception as e:
            logger.error(f"Error fetching website: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _crawl_page(self, session, url: str, base_url: str, visited: set, 
                          pages: list, max_pages: int, output_path: Path):
        """Recursively crawl website pages"""
        if len(visited) >= max_pages or url in visited:
            return
        
        if not url.startswith(base_url):
            return
        
        visited.add(url)
        
        try:
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    return
                
                content = await response.text()
                soup = BeautifulSoup(content, 'lxml')
                
                page_name = url.replace(base_url, '').strip('/').replace('/', '_') or 'index'
                if not page_name.endswith('.html'):
                    page_name += '.html'
                
                file_path = output_path / page_name
                file_path.write_text(content, encoding='utf-8')
                
                pages.append({
                    "url": url,
                    "file_path": str(file_path),
                    "title": soup.title.string if soup.title else page_name
                })
                
                logger.info(f"Downloaded: {url}")
                
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    if not isinstance(href, str):
                        continue
                    
                    if href.startswith('/'):
                        next_url = base_url.rstrip('/') + href
                    elif href.startswith('http'):
                        next_url = href
                    else:
                        next_url = url.rstrip('/') + '/' + href
                    
                    if len(visited) < max_pages:
                        await self._crawl_page(session, next_url, base_url, visited, 
                                               pages, max_pages, output_path)
                        
        except Exception as e:
            logger.warning(f"Error crawling {url}: {e}")
    
    def _collect_documentation_files(self, path: Path) -> List[Dict]:
        """Collect all documentation files from a directory"""
        files = []
        doc_extensions = {'.md', '.rst', '.html', '.txt'}
        
        for file_path in path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in doc_extensions:
                files.append({
                    "path": str(file_path),
                    "relative_path": str(file_path.relative_to(path)),
                    "extension": file_path.suffix,
                    "size": file_path.stat().st_size
                })
        
        return files
