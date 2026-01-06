"""Model for protocol research logging."""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class ProtocolResearchLog(BaseModel):
    """Log entry for protocol research API calls."""
    user_id: Optional[str] = Field(default=None, description="User ID (UUID)")
    protocol_name: str = Field(description="Name of the protocol researched")
    research_mode: str = Field(description="Research mode: 'quick' or 'deep'")
    source: str = Field(description="Source of response: 'knowledge_base', 'firecrawl', or 'ai_general'")
    duration_ms: Optional[int] = Field(default=None, description="Duration in milliseconds")
    firecrawl_cost: Optional[float] = Field(default=None, description="Cost of Firecrawl call (if applicable)")
    source_urls: Optional[List[str]] = Field(default=None, description="Source URLs used")
    success: bool = Field(default=True, description="Whether the research was successful")
    error_message: Optional[str] = Field(default=None, description="Error message if unsuccessful")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Timestamp of research")
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Last updated timestamp")

    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ProtocolResearchLogResponse(BaseModel):
    """Response model for research log queries."""
    id: int = Field(description="Log entry ID")
    user_id: Optional[str] = Field(description="User ID")
    protocol_name: str = Field(description="Protocol name")
    research_mode: str = Field(description="Research mode")
    source: str = Field(description="Response source")
    duration_ms: Optional[int] = Field(description="Duration in milliseconds")
    firecrawl_cost: Optional[float] = Field(description="Firecrawl cost")
    success: bool = Field(description="Success status")
    created_at: datetime = Field(description="Creation timestamp")


class ResearchAnalytics(BaseModel):
    """Analytics summary for protocol research."""
    total_searches: int = Field(description="Total number of searches")
    quick_searches: int = Field(description="Number of quick searches")
    deep_searches: int = Field(description="Number of deep searches")
    kb_hits: int = Field(description="Knowledge base hits")
    ai_fallbacks: int = Field(description="AI fallback uses")
    firecrawl_uses: int = Field(description="Firecrawl API uses")
    success_rate: float = Field(description="Success rate (0.0-1.0)")
    avg_duration_ms: float = Field(description="Average duration in milliseconds")
    total_firecrawl_cost: float = Field(description="Total Firecrawl cost")
    most_searched_protocols: List[tuple] = Field(description="List of (protocol, count) tuples")
