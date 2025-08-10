# processors/__init__.py
"""
Módulo de procesadores de documentos
"""

from .pdf_processor import PDFProcessor
from .docx_processor import DOCXProcessor
from .txt_processor import TXTProcessor
from .image_processor import ImageProcessor

__all__ = [
    'PDFProcessor',
    'DOCXProcessor', 
    'TXTProcessor',
    'ImageProcessor'
]