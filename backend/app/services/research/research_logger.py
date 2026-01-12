"""Service for logging protocol research API calls."""
import logging
import time
from typing import Optional, List
from datetime import datetime

from app.models.protocol_research_log import ProtocolResearchLog

logger = logging.getLogger(__name__)


class ResearchLogger:
    """Logs protocol research API calls for analytics and cost tracking."""
    
    def __init__(self):
        """Initialize the research logger."""
        self.pending_logs: List[ProtocolResearchLog] = []
    
    def start_timer(self) -> float:
        """Start a timer for measuring research duration."""
        return time.time()
    
    def calculate_duration_ms(self, start_time: float) -> int:
        """Calculate duration in milliseconds from start time."""
        elapsed = time.time() - start_time
        return int(elapsed * 1000)
    
    def log_research(
        self,
        protocol_name: str,
        research_mode: str,
        source: str,
        duration_ms: int,
        user_id: Optional[str] = None,
        firecrawl_cost: Optional[float] = None,
        source_urls: Optional[List[str]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> ProtocolResearchLog:
        """
        Log a protocol research API call.
        
        Args:
            protocol_name: Name of the protocol researched
            research_mode: Mode used ('quick' or 'deep')
            source: Source of response ('knowledge_base', 'firecrawl', or 'ai_general')
            duration_ms: Duration in milliseconds
            user_id: Optional user ID
            firecrawl_cost: Optional cost of Firecrawl call
            source_urls: Optional list of source URLs used
            success: Whether the research was successful
            error_message: Optional error message if unsuccessful
            
        Returns:
            ProtocolResearchLog instance
        """
        log_entry = ProtocolResearchLog(
            user_id=user_id,
            protocol_name=protocol_name,
            research_mode=research_mode,
            source=source,
            duration_ms=duration_ms,
            firecrawl_cost=firecrawl_cost,
            source_urls=source_urls,
            success=success,
            error_message=error_message,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        # Store in pending logs
        self.pending_logs.append(log_entry)
        
        logger.info(
            f"Research logged: {protocol_name} ({research_mode}) via {source} "
            f"(duration: {duration_ms}ms, success: {success})"
        )
        
        return log_entry
    
    def get_pending_logs(self) -> List[ProtocolResearchLog]:
        """Get all pending logs for batch insertion."""
        return self.pending_logs.copy()
    
    def clear_pending_logs(self) -> None:
        """Clear pending logs after successful batch insert."""
        self.pending_logs.clear()
    
    def calculate_firecrawl_cost(self, urls_scraped: int) -> float:
        """
        Calculate Firecrawl API cost based on URLs scraped.
        Current pricing: ~$0.05 per URL (may vary).
        
        Args:
            urls_scraped: Number of URLs scraped
            
        Returns:
            Estimated cost in USD
        """
        # Standard Firecrawl pricing: $0.05 per URL
        cost_per_url = 0.05
        return urls_scraped * cost_per_url


# Global instance for use across the application
research_logger = ResearchLogger()
