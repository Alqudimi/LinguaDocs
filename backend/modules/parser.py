import re
import markdown
from bs4 import BeautifulSoup
import frontmatter
from pathlib import Path
from typing import List, Dict, Tuple
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContentParser:
    """Parses documentation content and extracts translatable text"""
    
    def __init__(self):
        self.md = markdown.Markdown(extensions=['fenced_code', 'codehilite', 'tables'])
        
    def parse_file(self, file_path: str) -> Dict:
        """
        Parse a documentation file and extract translatable content
        
        Args:
            file_path: Path to the documentation file
            
        Returns:
            Dict containing parsed content with metadata
        """
        path = Path(file_path)
        
        if not path.exists():
            return {"status": "error", "message": "File not found"}
        
        try:
            content = path.read_text(encoding='utf-8')
            
            if path.suffix == '.md':
                return self._parse_markdown(content, file_path)
            elif path.suffix in ['.html', '.htm']:
                return self._parse_html(content, file_path)
            elif path.suffix == '.rst':
                return self._parse_restructured_text(content, file_path)
            else:
                return self._parse_plain_text(content, file_path)
                
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            return {"status": "error", "message": str(e)}
    
    def _parse_markdown(self, content: str, file_path: str) -> Dict:
        """Parse Markdown content"""
        post = frontmatter.loads(content)
        
        metadata = dict(post.metadata) if post.metadata else {}
        body = post.content
        
        translatable_blocks = []
        code_blocks = []
        
        code_pattern = r'```[\s\S]*?```|`[^`]+`'
        code_matches = list(re.finditer(code_pattern, body))
        
        current_pos = 0
        for match in code_matches:
            if match.start() > current_pos:
                text = body[current_pos:match.start()].strip()
                if text:
                    translatable_blocks.extend(self._split_into_blocks(text))
            
            code_blocks.append({
                "type": "code",
                "content": match.group(),
                "position": match.start()
            })
            current_pos = match.end()
        
        if current_pos < len(body):
            text = body[current_pos:].strip()
            if text:
                translatable_blocks.extend(self._split_into_blocks(text))
        
        return {
            "status": "success",
            "file_path": file_path,
            "file_type": "markdown",
            "metadata": metadata,
            "translatable_blocks": translatable_blocks,
            "code_blocks": code_blocks,
            "total_blocks": len(translatable_blocks),
            "original_content": content
        }
    
    def _parse_html(self, content: str, file_path: str) -> Dict:
        """Parse HTML content"""
        soup = BeautifulSoup(content, 'lxml')
        
        for script in soup(['script', 'style', 'code', 'pre']):
            script.decompose()
        
        translatable_blocks = []
        
        for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th', 'div']):
            text = element.get_text(strip=True)
            if text and len(text) > 3:
                translatable_blocks.append({
                    "type": "text",
                    "content": text,
                    "tag": element.name
                })
        
        return {
            "status": "success",
            "file_path": file_path,
            "file_type": "html",
            "translatable_blocks": translatable_blocks,
            "total_blocks": len(translatable_blocks),
            "original_content": content
        }
    
    def _parse_restructured_text(self, content: str, file_path: str) -> Dict:
        """Parse reStructuredText content"""
        code_pattern = r'\.\. code-block::[\s\S]*?(?=\n\n|\Z)|::\n\n(?: {4}.*\n)+'
        
        translatable_blocks = []
        code_blocks = []
        
        code_matches = list(re.finditer(code_pattern, content))
        
        current_pos = 0
        for match in code_matches:
            if match.start() > current_pos:
                text = content[current_pos:match.start()].strip()
                if text:
                    translatable_blocks.extend(self._split_into_blocks(text))
            
            code_blocks.append({
                "type": "code",
                "content": match.group(),
                "position": match.start()
            })
            current_pos = match.end()
        
        if current_pos < len(content):
            text = content[current_pos:].strip()
            if text:
                translatable_blocks.extend(self._split_into_blocks(text))
        
        return {
            "status": "success",
            "file_path": file_path,
            "file_type": "restructuredtext",
            "translatable_blocks": translatable_blocks,
            "code_blocks": code_blocks,
            "total_blocks": len(translatable_blocks),
            "original_content": content
        }
    
    def _parse_plain_text(self, content: str, file_path: str) -> Dict:
        """Parse plain text content"""
        blocks = self._split_into_blocks(content)
        
        return {
            "status": "success",
            "file_path": file_path,
            "file_type": "text",
            "translatable_blocks": blocks,
            "total_blocks": len(blocks),
            "original_content": content
        }
    
    def _split_into_blocks(self, text: str) -> List[Dict]:
        """Split text into translatable blocks (paragraphs, headings, etc.)"""
        blocks = []
        
        lines = text.split('\n')
        current_block = []
        
        for line in lines:
            line = line.strip()
            
            if not line:
                if current_block:
                    block_text = ' '.join(current_block)
                    if block_text:
                        blocks.append({
                            "type": "text",
                            "content": block_text
                        })
                    current_block = []
            else:
                current_block.append(line)
        
        if current_block:
            block_text = ' '.join(current_block)
            if block_text:
                blocks.append({
                    "type": "text",
                    "content": block_text
                })
        
        return blocks
    
    def parse_batch(self, file_paths: List[str]) -> Dict:
        """Parse multiple files"""
        results = []
        
        for file_path in file_paths:
            result = self.parse_file(file_path)
            results.append(result)
        
        total_blocks = sum(r.get('total_blocks', 0) for r in results if r.get('status') == 'success')
        
        return {
            "status": "success",
            "total_files": len(file_paths),
            "total_blocks": total_blocks,
            "results": results
        }
