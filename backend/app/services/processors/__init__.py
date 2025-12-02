"""
Processors module for command processing.
Provides modular, domain-specific processors for different command types.
"""
from .registry import ProcessorRegistry
from .base_processor import BaseProcessor

__all__ = ['ProcessorRegistry', 'BaseProcessor']
