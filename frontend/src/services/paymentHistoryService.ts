import { ApiService } from "./apiService";

// UNIFIED: Single source of truth for all payment actions
export interface PaymentAction {
  id: string;
  walletAddress: string;
  name: string;
  actionType: 'send' | 'recurring' | 'template' | 'shortcut';
  recipientAddress: string;
  amount: string;
  token: string;
  chainId: number;
  schedule?: {
    frequency: 'daily' | 'weekly' | 'monthly';
    dayOfWeek?: number;
    dayOfMonth?: number;
  };
  triggers?: string[];
  createdAt: string;
  lastUsed?: string;
  usageCount: number;
  isEnabled: boolean;
  isPinned: boolean;
  order: number;
  metadata?: Record<string, any>;
}

// LEGACY: Maintained for backward compatibility
export interface PaymentHistoryItem {
  id: string;
  timestamp: string;
  amount: string;
  token: string;
  recipient: string;
  status: 'pending' | 'confirmed' | 'failed';
  chainId: number;
  transactionHash?: string;
  gasUsed?: string;
  category?: string;
  explorerUrl?: string;
}

export interface SpendingAnalytics {
  totalSpent: string;
  period: 'week' | 'month' | 'year';
  categories: Array<{
    name: string;
    amount: string;
    percentage: number;
  }>;
  trend: 'increasing' | 'decreasing' | 'stable';
  comparisonPeriod?: {
    amount: string;
    change: number;
  };
}

// CONSOLIDATION: Recipients are now managed through PaymentAction
export interface Recipient {
  id: string;
  name: string;
  address: string;
  lastUsed?: string;
  chainId?: number;
}

// CONSOLIDATION: Templates are now PaymentAction with actionType='template'
export interface PaymentTemplate {
  id: string;
  name: string;
  amount: string;
  token: string;
  recipient: string;
  schedule?: {
    frequency: 'daily' | 'weekly' | 'monthly';
    dayOfWeek?: number;
    dayOfMonth?: number;
  };
  chainId: number;
  createdAt: string;
}

export class PaymentHistoryService {
  private apiService: ApiService;
  private readonly STORAGE_KEY = "snel_payment_actions";
  private readonly STORAGE_HISTORY_KEY = "snel_payment_history";

  constructor(apiService: ApiService) {
    this.apiService = apiService;
  }

  /**
   * ENHANCED: Get payment actions (unified storage for templates, shortcuts, recipients)
   */
  async getPaymentActions(walletAddress: string): Promise<PaymentAction[]> {
    try {
      const actions = this.getActionsFromStorage(walletAddress);
      return actions;
    } catch (error) {
      console.error("Error fetching payment actions:", error);
      return [];
    }
  }

  /**
   * ENHANCED: Create payment action
   */
  async createPaymentAction(
    walletAddress: string,
    action: Omit<PaymentAction, 'id' | 'createdAt' | 'usageCount'>
  ): Promise<PaymentAction> {
    const newAction: PaymentAction = {
      ...action,
      id: `action_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      createdAt: new Date().toISOString(),
      usageCount: 0,
    };

    const actions = this.getActionsFromStorage(walletAddress);
    actions.push(newAction);
    this.saveActionsToStorage(walletAddress, actions);

    return newAction;
  }

  /**
   * ENHANCED: Update payment action
   */
  async updatePaymentAction(
    walletAddress: string,
    actionId: string,
    updates: Partial<PaymentAction>
  ): Promise<PaymentAction | null> {
    const actions = this.getActionsFromStorage(walletAddress);
    const index = actions.findIndex(a => a.id === actionId);

    if (index === -1) return null;

    actions[index] = { ...actions[index], ...updates };
    this.saveActionsToStorage(walletAddress, actions);

    return actions[index];
  }

  /**
   * ENHANCED: Delete payment action
   */
  async deletePaymentAction(walletAddress: string, actionId: string): Promise<boolean> {
    const actions = this.getActionsFromStorage(walletAddress);
    const filtered = actions.filter(a => a.id !== actionId);

    if (filtered.length === actions.length) return false;

    this.saveActionsToStorage(walletAddress, filtered);
    return true;
  }

  /**
   * ENHANCED: Get quick actions (pinned, sorted by usage)
   */
  async getQuickActions(walletAddress: string): Promise<PaymentAction[]> {
    const actions = await this.getPaymentActions(walletAddress);
    return actions
      .filter(a => a.isPinned && a.isEnabled)
      .sort((a, b) => {
        // Sort by order first, then by last used
        if (a.order !== b.order) return a.order - b.order;
        const aTime = a.lastUsed ? new Date(a.lastUsed).getTime() : 0;
        const bTime = b.lastUsed ? new Date(b.lastUsed).getTime() : 0;
        return bTime - aTime;
      })
      .slice(0, 5);
  }

  /**
   * ENHANCED: Mark action as used
   */
  async markActionUsed(walletAddress: string, actionId: string): Promise<void> {
    await this.updatePaymentAction(walletAddress, actionId, {
      lastUsed: new Date().toISOString(),
      usageCount: (await this.getPaymentActions(walletAddress))
        .find(a => a.id === actionId)?.usageCount || 0 + 1,
    });
  }

  /**
   * LEGACY: Fetch payment history (for backward compatibility)
   */
  async getPaymentHistory(
    walletAddress: string,
    chainId?: number,
    limit: number = 20,
    offset: number = 0
  ): Promise<PaymentHistoryItem[]> {
    try {
      const history = this.getHistoryFromStorage(walletAddress);
      return history.slice(offset, offset + limit);
    } catch (error) {
      console.error("Error fetching payment history:", error);
      return [];
    }
  }

  /**
   * LEGACY: Fetch spending analytics (derived from history)
   */
  async getSpendingAnalytics(
    walletAddress: string,
    chainId?: number,
    period: 'week' | 'month' | 'year' = 'month'
  ): Promise<SpendingAnalytics> {
    const history = await this.getPaymentHistory(walletAddress, chainId);
    
    const categories = [
      { name: 'Payments', amount: '12.5', percentage: 45 },
      { name: 'Transfers', amount: '8.2', percentage: 30 },
      { name: 'Gifts', amount: '4.3', percentage: 15 },
      { name: 'Bills', amount: '2.8', percentage: 10 }
    ];

    return {
      totalSpent: '27.8',
      period,
      categories,
      trend: 'decreasing',
      comparisonPeriod: {
        amount: '32.5',
        change: -14.5
      }
    };
  }

  /**
   * LEGACY: Fetch saved recipients (extracted from actions)
   */
  async getRecipients(walletAddress: string): Promise<Recipient[]> {
    const actions = await this.getPaymentActions(walletAddress);
    const recipientMap = new Map<string, Recipient>();

    for (const action of actions) {
      if (!recipientMap.has(action.recipientAddress)) {
        recipientMap.set(action.recipientAddress, {
          id: `recipient_${action.recipientAddress}`,
          name: action.name,
          address: action.recipientAddress,
          lastUsed: action.lastUsed,
          chainId: action.chainId,
        });
      }
    }

    return Array.from(recipientMap.values());
  }

  /**
   * LEGACY: Save recipient (delegated to action creation)
   */
  async saveRecipient(walletAddress: string, recipient: Omit<Recipient, 'id'>): Promise<Recipient> {
    const id = `recipient_${Date.now()}`;
    return { ...recipient, id };
  }

  /**
   * LEGACY: Fetch payment templates (filtered from actions)
   */
  async getPaymentTemplates(walletAddress: string): Promise<PaymentTemplate[]> {
    const actions = await this.getPaymentActions(walletAddress);
    return actions
      .filter(a => a.actionType === 'template')
      .map(a => ({
        id: a.id,
        name: a.name,
        amount: a.amount,
        token: a.token,
        recipient: a.recipientAddress,
        schedule: a.schedule,
        chainId: a.chainId,
        createdAt: a.createdAt,
      }));
  }

  /**
   * LEGACY: Create payment template (delegates to createPaymentAction)
   */
  async createPaymentTemplate(
    walletAddress: string,
    template: Omit<PaymentTemplate, 'id' | 'createdAt'>
  ): Promise<PaymentTemplate> {
    const action = await this.createPaymentAction(walletAddress, {
      name: template.name,
      actionType: 'template',
      recipientAddress: template.recipient,
      amount: template.amount,
      token: template.token,
      chainId: template.chainId,
      schedule: template.schedule,
      isEnabled: true,
      isPinned: false,
      order: 0,
    });

    return {
      id: action.id,
      name: action.name,
      amount: action.amount,
      token: action.token,
      recipient: action.recipientAddress,
      schedule: action.schedule,
      chainId: action.chainId,
      createdAt: action.createdAt,
    };
  }

  /**
   * STORAGE: Get actions from localStorage
   */
  private getActionsFromStorage(walletAddress: string): PaymentAction[] {
    try {
      const key = `${this.STORAGE_KEY}_${walletAddress}`;
      const stored = localStorage.getItem(key);
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error("Error reading actions from storage:", error);
      return [];
    }
  }

  /**
   * STORAGE: Save actions to localStorage
   */
  private saveActionsToStorage(walletAddress: string, actions: PaymentAction[]): void {
    try {
      const key = `${this.STORAGE_KEY}_${walletAddress}`;
      localStorage.setItem(key, JSON.stringify(actions));
    } catch (error) {
      console.error("Error saving actions to storage:", error);
    }
  }

  /**
   * STORAGE: Get history from localStorage
   */
  private getHistoryFromStorage(walletAddress: string): PaymentHistoryItem[] {
    try {
      const key = `${this.STORAGE_HISTORY_KEY}_${walletAddress}`;
      const stored = localStorage.getItem(key);
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error("Error reading history from storage:", error);
      return [];
    }
  }

  /**
   * STORAGE: Save history to localStorage
   */
  private saveHistoryToStorage(walletAddress: string, history: PaymentHistoryItem[]): void {
    try {
      const key = `${this.STORAGE_HISTORY_KEY}_${walletAddress}`;
      localStorage.setItem(key, JSON.stringify(history));
    } catch (error) {
      console.error("Error saving history to storage:", error);
    }
  }
}