/**
 * useBridgeStatus - Real-time bridge status tracking
 * 
 * Monitors Axelar GMP bridge progress with polling/WebSocket support.
 * Follows MODULAR principle: independent, reusable hook.
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import type { BridgeStatusContent } from '../types/responses';

interface UseBridgeStatusOptions {
  bridgeId: string;
  onStatusUpdate?: (status: BridgeStatusContent) => void;
  onError?: (error: string) => void;
  pollInterval?: number; // milliseconds, defaults to 5000
  maxRetries?: number;
}

interface UseBridgeStatusReturn {
  status: BridgeStatusContent | null;
  isLoading: boolean;
  error: string | null;
  progress: number; // 0-100
  isComplete: boolean;
  isFailed: boolean;
}

/**
 * Hook to track bridge transaction status in real-time
 * 
 * Uses polling to fetch bridge status from backend.
 * Can be extended to use WebSocket for real-time updates.
 */
export const useBridgeStatus = ({
  bridgeId,
  onStatusUpdate,
  onError,
  pollInterval = 5000,
  maxRetries = 12, // 60 seconds total with 5s interval
}: UseBridgeStatusOptions): UseBridgeStatusReturn => {
  const [status, setStatus] = useState<BridgeStatusContent | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const retryCountRef = useRef(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`/api/bridge/status/${bridgeId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Status fetch failed: ${response.statusText}`);
      }

      const data = (await response.json()) as BridgeStatusContent;
      setStatus(data);
      setError(null);
      retryCountRef.current = 0;

      // Notify listener
      if (onStatusUpdate) {
        onStatusUpdate(data);
      }

      // Stop polling if complete or failed
      if (data.status === 'completed' || data.status === 'failed') {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMsg);

      // Retry with exponential backoff
      retryCountRef.current += 1;
      if (retryCountRef.current >= maxRetries) {
        if (onError) {
          onError(`Bridge status tracking failed after ${maxRetries} attempts`);
        }
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      }
    } finally {
      setIsLoading(false);
    }
  }, [bridgeId, onStatusUpdate, onError, maxRetries]);

  // Initial fetch and polling setup
  useEffect(() => {
    // Fetch immediately
    fetchStatus();

    // Set up polling
    intervalRef.current = setInterval(fetchStatus, pollInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [bridgeId, fetchStatus, pollInterval]);

  // Calculate progress (0-100)
  const progress =
    status && status.total_steps > 0
      ? Math.round((status.current_step / status.total_steps) * 100)
      : 0;

  const isComplete = status?.status === 'completed';
  const isFailed = status?.status === 'failed';

  return {
    status,
    isLoading,
    error,
    progress,
    isComplete,
    isFailed,
  };
};
