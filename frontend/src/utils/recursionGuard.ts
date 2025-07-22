/**
 * Recursion Guard Utility
 * Prevents infinite recursion in wallet operations and event handlers
 */

interface CallTracker {
  count: number;
  lastCall: number;
  timeout?: NodeJS.Timeout;
}

class RecursionGuard {
  private callTrackers = new Map<string, CallTracker>();
  private readonly MAX_CALLS = 5;
  private readonly TIME_WINDOW = 1000; // 1 second
  private readonly COOLDOWN_PERIOD = 2000; // 2 seconds

  /**
   * Check if a function call should be allowed or blocked due to recursion
   */
  canExecute(functionName: string): boolean {
    const now = Date.now();
    const tracker = this.callTrackers.get(functionName);

    if (!tracker) {
      // First call - allow and track
      this.callTrackers.set(functionName, {
        count: 1,
        lastCall: now
      });
      return true;
    }

    // Check if we're in a cooldown period
    if (now - tracker.lastCall < this.COOLDOWN_PERIOD && tracker.count >= this.MAX_CALLS) {
      console.warn(`[RecursionGuard] Function "${functionName}" is in cooldown period`);
      return false;
    }

    // Reset counter if enough time has passed
    if (now - tracker.lastCall > this.TIME_WINDOW) {
      tracker.count = 1;
      tracker.lastCall = now;
      return true;
    }

    // Increment counter
    tracker.count++;
    tracker.lastCall = now;

    // Check if we've exceeded the limit
    if (tracker.count > this.MAX_CALLS) {
      console.error(`[RecursionGuard] Potential infinite recursion detected in "${functionName}". Blocking further calls.`);
      
      // Set a timeout to reset after cooldown period
      if (tracker.timeout) {
        clearTimeout(tracker.timeout);
      }
      
      tracker.timeout = setTimeout(() => {
        this.reset(functionName);
      }, this.COOLDOWN_PERIOD);
      
      return false;
    }

    return true;
  }

  /**
   * Reset the call tracker for a specific function
   */
  reset(functionName: string): void {
    const tracker = this.callTrackers.get(functionName);
    if (tracker?.timeout) {
      clearTimeout(tracker.timeout);
    }
    this.callTrackers.delete(functionName);
  }

  /**
   * Reset all call trackers
   */
  resetAll(): void {
    for (const [, tracker] of this.callTrackers) {
      if (tracker.timeout) {
        clearTimeout(tracker.timeout);
      }
    }
    this.callTrackers.clear();
  }

  /**
   * Get current status of all tracked functions
   */
  getStatus(): Record<string, { count: number; blocked: boolean }> {
    const status: Record<string, { count: number; blocked: boolean }> = {};
    const now = Date.now();
    
    for (const [functionName, tracker] of this.callTrackers) {
      status[functionName] = {
        count: tracker.count,
        blocked: tracker.count > this.MAX_CALLS && (now - tracker.lastCall < this.COOLDOWN_PERIOD)
      };
    }
    
    return status;
  }
}

// Create singleton instance
export const recursionGuard = new RecursionGuard();

/**
 * Decorator function to protect against recursion
 */
export function withRecursionGuard<T extends (...args: any[]) => any>(
  fn: T,
  functionName?: string
): T {
  const name = functionName || fn.name || 'anonymous';
  
  return ((...args: any[]) => {
    if (!recursionGuard.canExecute(name)) {
      console.warn(`[RecursionGuard] Blocked recursive call to "${name}"`);
      return Promise.reject(new Error(`Recursive call blocked: ${name}`));
    }
    
    try {
      return fn(...args);
    } catch (error) {
      // Reset on error to prevent permanent blocking
      recursionGuard.reset(name);
      throw error;
    }
  }) as T;
}

/**
 * Async version of recursion guard decorator
 */
export function withAsyncRecursionGuard<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  functionName?: string
): T {
  const name = functionName || fn.name || 'anonymous';
  
  return (async (...args: any[]) => {
    if (!recursionGuard.canExecute(name)) {
      console.warn(`[RecursionGuard] Blocked recursive call to "${name}"`);
      throw new Error(`Recursive call blocked: ${name}`);
    }
    
    try {
      return await fn(...args);
    } catch (error) {
      // Reset on error to prevent permanent blocking
      recursionGuard.reset(name);
      throw error;
    }
  }) as T;
}

/**
 * Manual guard for inline use
 */
export function guardExecution(functionName: string, callback: () => any): any {
  if (!recursionGuard.canExecute(functionName)) {
    console.warn(`[RecursionGuard] Blocked recursive execution of "${functionName}"`);
    return null;
  }
  
  try {
    return callback();
  } catch (error) {
    recursionGuard.reset(functionName);
    throw error;
  }
}

/**
 * Async manual guard for inline use
 */
export async function guardAsyncExecution(functionName: string, callback: () => Promise<any>): Promise<any> {
  if (!recursionGuard.canExecute(functionName)) {
    console.warn(`[RecursionGuard] Blocked recursive execution of "${functionName}"`);
    return null;
  }
  
  try {
    return await callback();
  } catch (error) {
    recursionGuard.reset(functionName);
    throw error;
  }
}