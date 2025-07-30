/**
 * Advanced retry utility with exponential backoff, circuit breaker, and metrics
 * 
 * Features:
 * - Configurable retry attempts
 * - Exponential backoff with jitter
 * - Custom retry conditions
 * - Timeout handling
 * - Circuit breaker pattern
 * - Metrics tracking
 * - Support for sync and async functions
 */

import { logger } from './logger';

// ======== Type Definitions ========

/**
 * Options for configuring retry behavior
 */
export interface RetryOptions {
  /** Maximum number of retry attempts (default: 3) */
  maxRetries?: number;
  /** Base delay between retries in milliseconds (default: 1000) */
  delay?: number;
  /** Maximum delay between retries in milliseconds (default: 30000) */
  maxDelay?: number;
  /** Type of backoff strategy (default: 'exponential') */
  backoff?: 'fixed' | 'linear' | 'exponential';
  /** Factor for exponential backoff (default: 2) */
  factor?: number;
  /** Add random jitter to delay to prevent thundering herd (default: true) */
  jitter?: boolean;
  /** Maximum jitter percentage (0-1, default: 0.25) */
  jitterFactor?: number;
  /** Timeout for each attempt in milliseconds (0 = no timeout, default: 0) */
  timeout?: number;
  /** Function to determine if an error should trigger retry (default: all errors) */
  retryCondition?: (error: any, attempt: number) => boolean;
  /** Function to execute before each retry (default: none) */
  onRetry?: (error: any, attempt: number) => void;
  /** Enable circuit breaker pattern (default: false) */
  circuitBreaker?: boolean;
  /** Number of failures before opening circuit (default: 5) */
  circuitBreakerThreshold?: number;
  /** Time in milliseconds to keep circuit open (default: 60000) */
  circuitBreakerResetTimeout?: number;
  /** Track metrics for this retry operation (default: true) */
  trackMetrics?: boolean;
  /** Unique name for this retry operation (for metrics) */
  operationName?: string;
}

/**
 * Metrics collected during retry operations
 */
export interface RetryMetrics {
  /** Total number of operations */
  operations: number;
  /** Number of successful operations (no retries needed) */
  successes: number;
  /** Number of operations that succeeded after retries */
  successesAfterRetry: number;
  /** Number of operations that failed even after retries */
  failures: number;
  /** Total number of retry attempts across all operations */
  totalRetries: number;
  /** Average number of retries per operation */
  avgRetries: number;
  /** Maximum retries used in a single operation */
  maxRetriesUsed: number;
  /** Average delay between retries (ms) */
  avgDelay: number;
  /** Number of operations that timed out */
  timeouts: number;
  /** Number of operations blocked by circuit breaker */
  circuitBreakerBlocks: number;
  /** Current circuit breaker states by operation name */
  circuitBreakerStates: Record<string, CircuitBreakerState>;
}

/**
 * Circuit breaker states
 */
export type CircuitBreakerState = 'closed' | 'open' | 'half-open';

/**
 * Error thrown when the circuit breaker is open
 */
export class CircuitBreakerOpenError extends Error {
  constructor(operationName: string) {
    super(`Circuit breaker is open for operation: ${operationName}`);
    this.name = 'CircuitBreakerOpenError';
  }
}

/**
 * Error thrown when an operation times out
 */
export class OperationTimeoutError extends Error {
  constructor(operationName: string, timeout: number) {
    super(`Operation ${operationName} timed out after ${timeout}ms`);
    this.name = 'OperationTimeoutError';
  }
}

/**
 * Error thrown when all retry attempts have been exhausted
 */
export class RetryError extends Error {
  public readonly cause: any;
  public readonly attempts: number;

  constructor(message: string, cause: any, attempts: number) {
    super(message);
    this.name = 'RetryError';
    this.cause = cause;
    this.attempts = attempts;
  }
}

// ======== Global Circuit Breaker State ========

/**
 * Circuit breaker state information
 */
interface CircuitBreakerInfo {
  state: CircuitBreakerState;
  failures: number;
  lastFailure: number;
  resetTimeout: number | null;
}

/**
 * Global circuit breaker registry
 */
const circuitBreakers = new Map<string, CircuitBreakerInfo>();

/**
 * Global metrics for all retry operations
 */
const globalMetrics: RetryMetrics = {
  operations: 0,
  successes: 0,
  successesAfterRetry: 0,
  failures: 0,
  totalRetries: 0,
  avgRetries: 0,
  maxRetriesUsed: 0,
  avgDelay: 0,
  timeouts: 0,
  circuitBreakerBlocks: 0,
  circuitBreakerStates: {},
};

// ======== Helper Functions ========

/**
 * Calculate delay with exponential backoff and optional jitter
 */
function calculateDelay(
  attempt: number,
  options: Required<RetryOptions>
): number {
  let delay: number;

  switch (options.backoff) {
    case 'fixed':
      delay = options.delay;
      break;
    case 'linear':
      delay = options.delay * attempt;
      break;
    case 'exponential':
    default:
      delay = options.delay * Math.pow(options.factor, attempt);
      break;
  }

  // Cap at max delay
  delay = Math.min(delay, options.maxDelay);

  // Add jitter if enabled
  if (options.jitter) {
    const jitterRange = delay * options.jitterFactor;
    delay = delay - jitterRange / 2 + Math.random() * jitterRange;
  }

  return delay;
}

/**
 * Check and update circuit breaker state
 */
function checkCircuitBreaker(
  operationName: string,
  options: Required<RetryOptions>
): boolean {
  // Get or create circuit breaker info
  let cbInfo = circuitBreakers.get(operationName);
  if (!cbInfo) {
    cbInfo = {
      state: 'closed',
      failures: 0,
      lastFailure: 0,
      resetTimeout: null,
    };
    circuitBreakers.set(operationName, cbInfo);
  }

  // Update global metrics
  globalMetrics.circuitBreakerStates[operationName] = cbInfo.state;

  // If circuit is open, check if it's time to try again
  if (cbInfo.state === 'open') {
    const now = Date.now();
    if (now - cbInfo.lastFailure >= options.circuitBreakerResetTimeout) {
      // Transition to half-open
      cbInfo.state = 'half-open';
      globalMetrics.circuitBreakerStates[operationName] = 'half-open';
      logger.debug(`Circuit breaker for ${operationName} transitioned to half-open state`);
      return true;
    }
    // Circuit still open, block the request
    globalMetrics.circuitBreakerBlocks++;
    return false;
  }

  // Circuit is closed or half-open, allow the request
  return true;
}

/**
 * Handle success for circuit breaker
 */
function handleCircuitBreakerSuccess(operationName: string): void {
  const cbInfo = circuitBreakers.get(operationName);
  if (cbInfo && cbInfo.state === 'half-open') {
    // Reset on successful half-open request
    cbInfo.state = 'closed';
    cbInfo.failures = 0;
    globalMetrics.circuitBreakerStates[operationName] = 'closed';
    logger.debug(`Circuit breaker for ${operationName} reset to closed state`);
  }
}

/**
 * Handle failure for circuit breaker
 */
function handleCircuitBreakerFailure(
  operationName: string,
  options: Required<RetryOptions>
): void {
  const cbInfo = circuitBreakers.get(operationName);
  if (!cbInfo) return;

  cbInfo.failures++;
  cbInfo.lastFailure = Date.now();

  if (
    cbInfo.state === 'half-open' ||
    (cbInfo.state === 'closed' && cbInfo.failures >= options.circuitBreakerThreshold)
  ) {
    // Open the circuit
    cbInfo.state = 'open';
    globalMetrics.circuitBreakerStates[operationName] = 'open';
    logger.warn(`Circuit breaker for ${operationName} opened after ${cbInfo.failures} failures`);
  }
}

/**
 * Create a promise that rejects after a timeout
 */
function createTimeout<T>(ms: number, operationName: string): Promise<T> {
  return new Promise<T>((_, reject) => {
    setTimeout(() => {
      globalMetrics.timeouts++;
      reject(new OperationTimeoutError(operationName, ms));
    }, ms);
  });
}

/**
 * Sleep for a specified duration
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ======== Core Retry Function ========

/**
 * Retry a function with configurable backoff strategy and circuit breaker
 * 
 * @param fn Function to retry (can be async or sync)
 * @param options Retry options
 * @returns Result of the function
 * @throws RetryError if all retries fail
 * @throws CircuitBreakerOpenError if circuit breaker is open
 * @throws OperationTimeoutError if operation times out
 */
export async function retry<T>(
  fn: () => T | Promise<T>,
  options: RetryOptions = {}
): Promise<T> {
  // Merge with defaults
  const mergedOptions: Required<RetryOptions> = {
    maxRetries: 3,
    delay: 1000,
    maxDelay: 30000,
    backoff: 'exponential',
    factor: 2,
    jitter: true,
    jitterFactor: 0.25,
    timeout: 0,
    retryCondition: () => true,
    onRetry: () => {},
    circuitBreaker: false,
    circuitBreakerThreshold: 5,
    circuitBreakerResetTimeout: 60000,
    trackMetrics: true,
    operationName: `retry-${Math.random().toString(36).substring(2, 9)}`,
    ...options
  };

  // Initialize metrics for this operation
  let retryCount = 0;
  let lastDelay = 0;
  let startTime = Date.now();

  if (mergedOptions.trackMetrics) {
    globalMetrics.operations++;
  }

  // Check circuit breaker if enabled
  if (mergedOptions.circuitBreaker) {
    const canProceed = checkCircuitBreaker(mergedOptions.operationName, mergedOptions);
    if (!canProceed) {
      if (mergedOptions.trackMetrics) {
        globalMetrics.failures++;
      }
      throw new CircuitBreakerOpenError(mergedOptions.operationName);
    }
  }

  // Execute with retries
  let lastError: any;
  for (let attempt = 0; attempt <= mergedOptions.maxRetries; attempt++) {
    try {
      let result: T;

      // Apply timeout if specified
      if (mergedOptions.timeout > 0) {
        result = await Promise.race([
          Promise.resolve().then(() => fn()),
          createTimeout<T>(mergedOptions.timeout, mergedOptions.operationName)
        ]);
      } else {
        result = await Promise.resolve().then(() => fn());
      }

      // Success - update circuit breaker and metrics
      if (mergedOptions.circuitBreaker) {
        handleCircuitBreakerSuccess(mergedOptions.operationName);
      }

      if (mergedOptions.trackMetrics) {
        if (attempt === 0) {
          globalMetrics.successes++;
        } else {
          globalMetrics.successesAfterRetry++;
          globalMetrics.totalRetries += attempt;
          globalMetrics.avgRetries = globalMetrics.totalRetries / 
            (globalMetrics.operations - globalMetrics.successes);
          globalMetrics.maxRetriesUsed = Math.max(globalMetrics.maxRetriesUsed, attempt);
          globalMetrics.avgDelay = (globalMetrics.avgDelay * (globalMetrics.totalRetries - attempt) + 
            lastDelay * attempt) / globalMetrics.totalRetries;
        }
      }

      return result;
    } catch (error) {
      lastError = error;

      // Check if we've exhausted all retries
      if (attempt >= mergedOptions.maxRetries) {
        break;
      }

      // Check if this error should trigger a retry
      if (!mergedOptions.retryCondition(error, attempt + 1)) {
        break;
      }

      // Calculate delay for next retry
      lastDelay = calculateDelay(attempt + 1, mergedOptions);

      // Call onRetry callback
      try {
        mergedOptions.onRetry(error, attempt + 1);
      } catch (callbackError) {
        logger.warn(`Error in retry callback for ${mergedOptions.operationName}:`, callbackError);
      }

      // Log retry attempt
      logger.debug(
        `Retry attempt ${attempt + 1}/${mergedOptions.maxRetries} for ${mergedOptions.operationName} ` +
        `after ${lastDelay}ms delay. Error: ${(error as any)?.message || error?.toString() || 'Unknown error'}`
      );

      // Wait before next attempt
      await sleep(lastDelay);
      retryCount++;
    }
  }

  // All retries failed - update circuit breaker and metrics
  if (mergedOptions.circuitBreaker) {
    handleCircuitBreakerFailure(mergedOptions.operationName, mergedOptions);
  }

  if (mergedOptions.trackMetrics) {
    globalMetrics.failures++;
    globalMetrics.totalRetries += retryCount;
    globalMetrics.avgRetries = globalMetrics.totalRetries / 
      (globalMetrics.operations - globalMetrics.successes);
    if (retryCount > 0) {
      globalMetrics.maxRetriesUsed = Math.max(globalMetrics.maxRetriesUsed, retryCount);
      globalMetrics.avgDelay = (globalMetrics.avgDelay * (globalMetrics.totalRetries - retryCount) + 
        lastDelay * retryCount) / globalMetrics.totalRetries;
    }
  }

  // Throw enhanced error with details
  throw new RetryError(
    `All ${mergedOptions.maxRetries} retry attempts failed for ${mergedOptions.operationName}`,
    lastError,
    retryCount
  );
}

// ======== Utility Functions ========

/**
 * Reset the circuit breaker for an operation
 */
export function resetCircuitBreaker(operationName: string): void {
  const cbInfo = circuitBreakers.get(operationName);
  if (cbInfo) {
    cbInfo.state = 'closed';
    cbInfo.failures = 0;
    globalMetrics.circuitBreakerStates[operationName] = 'closed';
    logger.log(`Circuit breaker for ${operationName} manually reset to closed state`);
  }
}

/**
 * Reset all circuit breakers
 */
export function resetAllCircuitBreakers(): void {
  for (const [name, cbInfo] of circuitBreakers.entries()) {
    cbInfo.state = 'closed';
    cbInfo.failures = 0;
    globalMetrics.circuitBreakerStates[name] = 'closed';
  }
  logger.log('All circuit breakers reset to closed state');
}

/**
 * Get the current state of all circuit breakers
 */
export function getCircuitBreakerStates(): Record<string, CircuitBreakerState> {
  const states: Record<string, CircuitBreakerState> = {};
  for (const [name, cbInfo] of circuitBreakers.entries()) {
    states[name] = cbInfo.state;
  }
  return states;
}

/**
 * Get retry metrics
 */
export function getRetryMetrics(): RetryMetrics {
  return { ...globalMetrics };
}

/**
 * Reset retry metrics
 */
export function resetRetryMetrics(): void {
  globalMetrics.operations = 0;
  globalMetrics.successes = 0;
  globalMetrics.successesAfterRetry = 0;
  globalMetrics.failures = 0;
  globalMetrics.totalRetries = 0;
  globalMetrics.avgRetries = 0;
  globalMetrics.maxRetriesUsed = 0;
  globalMetrics.avgDelay = 0;
  globalMetrics.timeouts = 0;
  globalMetrics.circuitBreakerBlocks = 0;
  // Keep circuit breaker states
}

/**
 * Create a retry function with predefined options
 */
export function createRetry(defaultOptions: RetryOptions) {
  return <T>(fn: () => T | Promise<T>, options: RetryOptions = {}) => 
    retry(fn, { ...defaultOptions, ...options });
}

/**
 * Retry with exponential backoff (convenience function)
 */
export function retryWithExponentialBackoff<T>(
  fn: () => T | Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000
): Promise<T> {
  return retry(fn, {
    maxRetries,
    delay: baseDelay,
    backoff: 'exponential',
    jitter: true
  });
}

/**
 * Retry with timeout (convenience function)
 */
export function retryWithTimeout<T>(
  fn: () => T | Promise<T>,
  timeout: number,
  maxRetries: number = 3
): Promise<T> {
  return retry(fn, {
    maxRetries,
    timeout,
    operationName: `timeout-retry-${timeout}ms`
  });
}

/**
 * Retry with circuit breaker (convenience function)
 */
export function retryWithCircuitBreaker<T>(
  fn: () => T | Promise<T>,
  operationName: string,
  maxRetries: number = 3
): Promise<T> {
  return retry(fn, {
    maxRetries,
    circuitBreaker: true,
    operationName
  });
}

// Default export
export default retry;
