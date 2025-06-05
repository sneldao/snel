import { AnalysisProgress, PortfolioAnalysis } from './portfolioService';

interface WebSocketCallbacks {
  onProgress?: (progress: AnalysisProgress) => void;
  onResult?: (result: PortfolioAnalysis) => void;
  onError?: (error: any) => void;
  onClose?: () => void;
  onOpen?: () => void;
}

export class WebSocketService {
  private socket: WebSocket | null = null;
  private baseUrl: string;
  private retryCount: number = 0;
  private maxRetries: number = 3;
  private retryDelay: number = 2000;
  private callbacks: WebSocketCallbacks = {};
  private connectPromise: Promise<void> | null = null;
  private connectResolve: (() => void) | null = null;
  private connectReject: ((reason?: any) => void) | null = null;

  constructor() {
    // Get WebSocket URL using the same logic as ApiService
    const isProduction = process.env.NODE_ENV === 'production';

    if (isProduction) {
      // In production, always use the Northflank backend URL
      this.baseUrl = 'wss://p02--snel-web-app--wxd25gkpcp8m.code.run/api/v1/ws';
    } else {
      // In development, check for API URL or use localhost
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const wsUrl = apiUrl.replace('http://', 'ws://').replace('https://', 'wss://');
      this.baseUrl = `${wsUrl}/api/v1/ws`;
    }

    console.log('WebSocket service initialized with baseUrl:', this.baseUrl);
  }

  /**
   * Connect to the WebSocket server for portfolio analysis
   */
  connect(walletAddress: string, chainId?: number, callbacks?: WebSocketCallbacks): Promise<void> {
    // Store callbacks
    this.callbacks = callbacks || {};

    // Create a promise that resolves when connection is established
    this.connectPromise = new Promise((resolve, reject) => {
      this.connectResolve = resolve;
      this.connectReject = reject;
      
      // Add timeout to reject the promise after 10 seconds
      setTimeout(() => {
        if (this.socket?.readyState !== WebSocket.OPEN) {
          console.log('WebSocket connection timeout');
          if (this.connectReject) {
            this.connectReject(new Error('Connection timeout'));
          }
          
          if (this.callbacks.onError) {
            this.callbacks.onError({
              message: 'Connection timeout after 10 seconds',
              code: 'CONNECTION_TIMEOUT'
            });
          }
          
          // Ensure socket is closed
          this.disconnect();
        }
      }, 10000);
    });

    // Build URL with query parameters
    let url = `${this.baseUrl}/portfolio/${walletAddress}`;
    if (chainId) {
      url += `?chain_id=${chainId}`;
    }

    console.log('Attempting WebSocket connection to:', url);

    // Close existing connection if any
    this.disconnect();

    try {
      // Create new WebSocket connection
      this.socket = new WebSocket(url);
      this.setupEventHandlers();
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      if (this.connectReject) {
        this.connectReject(error);
      }
      
      if (this.callbacks.onError) {
        this.callbacks.onError({
          message: 'Failed to create WebSocket connection',
          error
        });
      }
    }

    return this.connectPromise;
  }

  /**
   * Setup WebSocket event handlers
   */
  private setupEventHandlers() {
    if (!this.socket) return;

    this.socket.onopen = () => {
      console.log('WebSocket connection established');
      this.retryCount = 0;
      
      if (this.callbacks.onOpen) {
        this.callbacks.onOpen();
      }

      if (this.connectResolve) {
        this.connectResolve();
      }
      
      // Send a ping immediately to test the connection
      try {
        this.socket?.send(JSON.stringify({ type: 'ping' }));
      } catch (e) {
        console.warn('Failed to send initial ping');
      }
    };

    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        
        switch (message.type) {
          case 'progress':
            if (this.callbacks.onProgress) {
              this.callbacks.onProgress(message.data);
            }
            break;
          
          case 'result':
            if (this.callbacks.onResult) {
              this.callbacks.onResult(message.data);
            }
            break;
          
          case 'error':
            if (this.callbacks.onError) {
              this.callbacks.onError(message.data);
            }
            break;
          
          default:
            console.warn('Unknown message type:', message.type);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
        if (this.callbacks.onError) {
          this.callbacks.onError({ message: 'Invalid server response', error });
        }
      }
    };

    this.socket.onclose = (event) => {
      // Don't retry if it was a normal closure
      const isAbnormalClosure = !event.wasClean;
      
      console.log(`WebSocket connection closed. Code: ${event.code}, Reason: ${event.reason}, Abnormal: ${isAbnormalClosure}`);
      
      if (this.callbacks.onClose) {
        this.callbacks.onClose();
      }

      // Only retry on abnormal closures, and only if we haven't reached max retries
      if (isAbnormalClosure && this.retryCount < this.maxRetries) {
        this.retryCount++;
        const delay = this.retryDelay * this.retryCount;
        
        console.log(`Retrying connection in ${delay}ms (attempt ${this.retryCount}/${this.maxRetries})`);
        
        if (this.callbacks.onProgress) {
          this.callbacks.onProgress({
            stage: `Connection lost. Retrying in ${delay / 1000} seconds...`,
            completion: 0,
            type: 'error'
          });
        }
        
        setTimeout(() => {
          if (this.socket?.url) {
            this.socket = new WebSocket(this.socket.url);
            this.setupEventHandlers();
          }
        }, delay);
      } else if (isAbnormalClosure) {
        // Max retries reached
        if (this.connectReject) {
          this.connectReject(new Error('Max connection retries reached'));
        }
        
        if (this.callbacks.onError) {
          this.callbacks.onError({
            message: 'Connection failed after multiple retries',
            code: 'CONNECTION_FAILED'
          });
        }
      }
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      
      if (this.callbacks.onError) {
        this.callbacks.onError({
          message: 'WebSocket connection error - the backend service may be unavailable',
          error,
          code: 'WEBSOCKET_ERROR'
        });
      }

      // Reject the connection promise if still pending
      if (this.connectReject) {
        this.connectReject(new Error('WebSocket connection failed'));
        // Clear the resolvers to avoid multiple rejections
        this.connectResolve = null;
        this.connectReject = null;
      }
      
      // Try an alternative method if WebSocket fails
      if (this.callbacks.onProgress) {
        this.callbacks.onProgress({
          stage: "WebSocket connection failed. Falling back to HTTP.",
          completion: 10,
          type: "progress",
          details: "The real-time connection failed, will use traditional requests instead."
        });
      }
    };
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect() {
    if (this.socket) {
      try {
        // Use code 1000 for normal closure
        this.socket.close(1000, 'Client disconnected');
      } catch (e) {
        console.warn('Error while closing WebSocket:', e);
      } finally {
        this.socket = null;
        
        // Clear any pending connection promises
        this.connectResolve = null;
        this.connectReject = null;
      }
    }
  }

  /**
   * Check if WebSocket is currently connected
   */
  isConnected(): boolean {
    return this.socket !== null && this.socket.readyState === WebSocket.OPEN;
  }

  /**
   * Get current connection state
   */
  getState(): string {
    if (!this.socket) return 'CLOSED';
    
    switch (this.socket.readyState) {
      case WebSocket.CONNECTING:
        return 'CONNECTING';
      case WebSocket.OPEN:
        return 'OPEN';
      case WebSocket.CLOSING:
        return 'CLOSING';
      case WebSocket.CLOSED:
        return 'CLOSED';
      default:
        return 'UNKNOWN';
    }
  }
}

// Create a singleton instance
export const websocketService = new WebSocketService();