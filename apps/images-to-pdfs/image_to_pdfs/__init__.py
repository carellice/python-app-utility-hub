"""Conversione in PDF delle immagini contenute in sottocartelle."""

from .converter import ConversionSummary, ExistingFilePolicy, ImageFolderConverter

__all__ = ["ConversionSummary", "ExistingFilePolicy", "ImageFolderConverter"]
__version__ = "1.0.0"
