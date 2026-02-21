"""Configuration management for RAG Quality Toolkit"""
import os
from pathlib import Path


class Config:
    """Configuration settings"""
    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    EVALUATE_RETRIEVAL: bool = os.getenv("EVALUATE_RETRIEVAL", "true").lower() == "true"
    EVALUATE_GENERATION: bool = os.getenv("EVALUATE_GENERATION", "true").lower() == "true"
    EVALUATE_END_TO_END: bool = os.getenv("EVALUATE_END_TO_END", "true").lower() == "true"
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "/app/reports"))
    
    @classmethod
    def validate(cls) -> None:
        """Validate configuration"""
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if cls.LOG_LEVEL.upper() not in valid_log_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_log_levels}")


Config.validate()

