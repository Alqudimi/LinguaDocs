import logging
from typing import List, Dict, Optional
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TranslationEngine:
    """Translation engine supporting multiple backends"""
    
    def __init__(self, model_type: str = "marian"):
        self.model_type = model_type
        self.model = None
        self.tokenizer = None
        self.supported_languages = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "ar": "Arabic",
            "hi": "Hindi"
        }
        
    async def load_model(self, source_lang: str = "en", target_lang: str = "es"):
        """
        Load translation model
        
        Args:
            source_lang: Source language code
            target_lang: Target language code
        """
        try:
            if self.model_type == "marian":
                from transformers import MarianMTModel, MarianTokenizer
                
                model_name = f"Helsinki-NLP/opus-mt-{source_lang}-{target_lang}"
                logger.info(f"Loading model: {model_name}")
                
                self.tokenizer = MarianTokenizer.from_pretrained(model_name)
                self.model = MarianMTModel.from_pretrained(model_name)
                
                logger.info("Model loaded successfully")
                return {"status": "success", "model": model_name}
            else:
                return {"status": "error", "message": f"Unsupported model type: {self.model_type}"}
                
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return {
                "status": "fallback",
                "message": f"Model loading failed: {e}. Using mock translation for demo."
            }
    
    async def translate_text(self, text: str, source_lang: str = "en", 
                            target_lang: str = "es") -> Dict:
        """
        Translate a single text block
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Dict with translated text
        """
        try:
            if not text or not text.strip():
                return {"status": "success", "translated_text": text}
            
            if self.model is None or self.tokenizer is None:
                await self.load_model(source_lang, target_lang)
            
            if self.model and self.tokenizer:
                inputs = self.tokenizer([text], return_tensors="pt", padding=True)
                translated = self.model.generate(**inputs)
                translated_text = self.tokenizer.decode(translated[0], skip_special_tokens=True)
                
                return {
                    "status": "success",
                    "original_text": text,
                    "translated_text": translated_text,
                    "source_lang": source_lang,
                    "target_lang": target_lang
                }
            else:
                translated_text = f"[{target_lang.upper()}] {text}"
                return {
                    "status": "mock",
                    "original_text": text,
                    "translated_text": translated_text,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "note": "Using mock translation for demo"
                }
                
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return {
                "status": "error",
                "message": str(e),
                "original_text": text
            }
    
    async def translate_batch(self, texts: List[str], source_lang: str = "en", 
                             target_lang: str = "es", batch_size: int = 8) -> Dict:
        """
        Translate multiple text blocks in batches
        
        Args:
            texts: List of texts to translate
            source_lang: Source language code
            target_lang: Target language code
            batch_size: Number of texts to process at once
            
        Returns:
            Dict with translation results
        """
        try:
            if self.model is None or self.tokenizer is None:
                await self.load_model(source_lang, target_lang)
            
            translated_texts = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                if self.model and self.tokenizer:
                    inputs = self.tokenizer(batch, return_tensors="pt", padding=True, truncation=True)
                    translated = self.model.generate(**inputs)
                    
                    for j, translation in enumerate(translated):
                        translated_text = self.tokenizer.decode(translation, skip_special_tokens=True)
                        translated_texts.append(translated_text)
                else:
                    for text in batch:
                        translated_texts.append(f"[{target_lang.upper()}] {text}")
                
                logger.info(f"Translated batch {i // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size}")
            
            return {
                "status": "success",
                "total_texts": len(texts),
                "translated_texts": translated_texts,
                "source_lang": source_lang,
                "target_lang": target_lang
            }
            
        except Exception as e:
            logger.error(f"Batch translation error: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def translate_document(self, parsed_content: Dict, source_lang: str = "en",
                                target_lang: str = "es") -> Dict:
        """
        Translate a parsed document while preserving structure
        
        Args:
            parsed_content: Parsed content from ContentParser
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Dict with translated document
        """
        try:
            if parsed_content.get("status") != "success":
                return {"status": "error", "message": "Invalid parsed content"}
            
            translatable_blocks = parsed_content.get("translatable_blocks", [])
            texts = [block["content"] for block in translatable_blocks]
            
            if not texts:
                return {
                    "status": "success",
                    "message": "No translatable content found",
                    "translated_content": parsed_content
                }
            
            translation_result = await self.translate_batch(texts, source_lang, target_lang)
            
            if translation_result.get("status") in ["success", "mock"]:
                translated_texts = translation_result["translated_texts"]
                
                for i, block in enumerate(translatable_blocks):
                    if i < len(translated_texts):
                        block["translated_content"] = translated_texts[i]
                        block["original_content"] = block["content"]
                
                translated_content = parsed_content.copy()
                translated_content["translatable_blocks"] = translatable_blocks
                translated_content["translation_metadata"] = {
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "total_blocks": len(translatable_blocks),
                    "status": translation_result.get("status")
                }
                
                return {
                    "status": "success",
                    "translated_content": translated_content
                }
            else:
                return translation_result
                
        except Exception as e:
            logger.error(f"Document translation error: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_supported_languages(self) -> Dict:
        """Get list of supported languages"""
        return {
            "status": "success",
            "languages": self.supported_languages
        }
