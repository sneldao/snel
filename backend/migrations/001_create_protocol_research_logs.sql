-- Migration: Create protocol_research_logs table
-- Version: 001
-- Date: 2025-01-06
-- Description: Creates the protocol_research_logs table for tracking research API usage and analytics

CREATE TABLE IF NOT EXISTS protocol_research_logs (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    protocol_name VARCHAR(255) NOT NULL,
    research_mode VARCHAR(20) NOT NULL,  -- 'quick' | 'deep'
    source VARCHAR(50) NOT NULL,  -- 'knowledge_base' | 'firecrawl' | 'ai_general'
    duration_ms INTEGER,
    firecrawl_cost DECIMAL(10, 4),  -- NULL if not used
    source_urls TEXT[],  -- Array of URLs used
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indices for common queries
CREATE INDEX idx_protocol_research_logs_user_id ON protocol_research_logs(user_id);
CREATE INDEX idx_protocol_research_logs_created_at ON protocol_research_logs(created_at);
CREATE INDEX idx_protocol_research_logs_research_mode ON protocol_research_logs(research_mode);
CREATE INDEX idx_protocol_research_logs_user_created ON protocol_research_logs(user_id, created_at);
CREATE INDEX idx_protocol_research_logs_mode_created ON protocol_research_logs(research_mode, created_at);

-- Add comment for documentation
COMMENT ON TABLE protocol_research_logs IS 'Tracks protocol research API calls for analytics, cost tracking, and usage monitoring';
COMMENT ON COLUMN protocol_research_logs.user_id IS 'Reference to the user who performed the research';
COMMENT ON COLUMN protocol_research_logs.research_mode IS 'Research mode used: quick (KB+AI) or deep (Firecrawl+AI)';
COMMENT ON COLUMN protocol_research_logs.source IS 'Source of the response: knowledge_base, firecrawl, or ai_general';
COMMENT ON COLUMN protocol_research_logs.duration_ms IS 'Total duration of the research in milliseconds';
COMMENT ON COLUMN protocol_research_logs.firecrawl_cost IS 'Cost of Firecrawl API call (if applicable)';
COMMENT ON COLUMN protocol_research_logs.source_urls IS 'Array of source URLs used in deep research';
