/**
 * Production-safe logging utility
 * Suppresses console output in production environment to reduce noise
 */

const isProduction = process.env.NODE_ENV === 'production';

export const logger = {
  /**
   * Log informational messages (suppressed in production)
   */
  log: (...args: any[]) => {
    if (!isProduction) {
      console.log(...args);
    }
  },

  /**
   * Log warnings (always shown but with production prefix)
   */
  warn: (...args: any[]) => {
    if (isProduction) {
      console.warn('[SNEL]', ...args);
    } else {
      console.warn(...args);
    }
  },

  /**
   * Log errors (always shown but with production prefix)
   */
  error: (...args: any[]) => {
    if (isProduction) {
      console.error('[SNEL]', ...args);
    } else {
      console.error(...args);
    }
  },

  /**
   * Log debug information (only in development)
   */
  debug: (...args: any[]) => {
    if (!isProduction) {
      console.log('[DEBUG]', ...args);
    }
  },

  /**
   * Log informational messages (alias for log method)
   */
  info: (...args: any[]) => {
    if (!isProduction) {
      console.log('[INFO]', ...args);
    }
  },

  /**
   * Log API requests (only in development)
   */
  api: (method: string, url: string, data?: any) => {
    if (!isProduction) {
      console.log(`[API] ${method} ${url}`, data ? JSON.stringify(data, null, 2) : '');
    }
  },

  /**
   * Log service initialization (only in development)
   */
  service: (serviceName: string, message: string) => {
    if (!isProduction) {
      console.log(`[${serviceName.toUpperCase()}]`, message);
    }
  }
};

/**
 * Suppress external library console noise in production
 */
export const suppressExternalConsoleNoise = () => {
  if (!isProduction) return;

  // Store original console methods
  const originalConsole = {
    log: console.log,
    warn: console.warn,
    error: console.error
  };

  // List of external library patterns to suppress
  const suppressPatterns = [
    /backpack/i,
    /ipfs/i,
    /certificate/i,
    /ssl/i,
    /tls/i,
    /websocket.*failed/i,
    /connection.*refused/i,
    /network.*error/i
  ];

  // Override console methods to filter external noise
  console.log = (...args: any[]) => {
    const message = args.join(' ');
    const shouldSuppress = suppressPatterns.some(pattern => pattern.test(message));
    
    if (!shouldSuppress) {
      originalConsole.log(...args);
    }
  };

  console.warn = (...args: any[]) => {
    const message = args.join(' ');
    const shouldSuppress = suppressPatterns.some(pattern => pattern.test(message));
    
    if (!shouldSuppress) {
      originalConsole.warn('[SNEL]', ...args);
    }
  };

  console.error = (...args: any[]) => {
    const message = args.join(' ');
    const shouldSuppress = suppressPatterns.some(pattern => pattern.test(message));
    
    if (!shouldSuppress) {
      originalConsole.error('[SNEL]', ...args);
    }
  };
};