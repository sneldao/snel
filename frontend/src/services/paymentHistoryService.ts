import { ApiService } from "./apiService";

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

export interface Recipient {
  id: string;
  name: string;
  address: string;
  lastUsed?: string;
  chainId?: number;
}

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

  constructor(apiService: ApiService) {
    this.apiService = apiService;
  }

  /**
   * Fetch payment history for the connected wallet
   */
  async getPaymentHistory(
    walletAddress: string,
    chainId?: number,
    limit: number = 20,
    offset: number = 0
  ): Promise<PaymentHistoryItem[]> {
    try {
      // For now, we'll simulate payment history data
      // In a real implementation, this would call a backend endpoint
      return this.generateMockPaymentHistory(walletAddress, chainId);
    } catch (error) {
      console.error("Error fetching payment history:", error);
      throw new Error("Failed to fetch payment history");
    }
  }

  /**
   * Fetch spending analytics for the connected wallet
   */
  async getSpendingAnalytics(
    walletAddress: string,
    chainId?: number,
    period: 'week' | 'month' | 'year' = 'month'
  ): Promise<SpendingAnalytics> {
    try {
      // For now, we'll simulate analytics data
      // In a real implementation, this would call a backend endpoint
      return this.generateMockSpendingAnalytics(walletAddress, chainId, period);
    } catch (error) {
      console.error("Error fetching spending analytics:", error);
      throw new Error("Failed to fetch spending analytics");
    }
  }

  /**
   * Fetch saved recipients for the connected wallet
   */
  async getRecipients(walletAddress: string): Promise<Recipient[]> {
    try {
      // For now, we'll simulate recipient data
      // In a real implementation, this would call a backend endpoint
      return this.generateMockRecipients(walletAddress);
    } catch (error) {
      console.error("Error fetching recipients:", error);
      throw new Error("Failed to fetch recipients");
    }
  }

  /**
   * Save a new recipient
   */
  async saveRecipient(walletAddress: string, recipient: Omit<Recipient, 'id'>): Promise<Recipient> {
    try {
      // For now, we'll simulate saving a recipient
      // In a real implementation, this would call a backend endpoint
      return {
        ...recipient,
        id: `recipient_${Date.now()}`,
      };
    } catch (error) {
      console.error("Error saving recipient:", error);
      throw new Error("Failed to save recipient");
    }
  }

  /**
   * Fetch payment templates for the connected wallet
   */
  async getPaymentTemplates(walletAddress: string): Promise<PaymentTemplate[]> {
    try {
      // For now, we'll simulate template data
      // In a real implementation, this would call a backend endpoint
      return this.generateMockPaymentTemplates(walletAddress);
    } catch (error) {
      console.error("Error fetching payment templates:", error);
      throw new Error("Failed to fetch payment templates");
    }
  }

  /**
   * Create a new payment template
   */
  async createPaymentTemplate(walletAddress: string, template: Omit<PaymentTemplate, 'id' | 'createdAt'>): Promise<PaymentTemplate> {
    try {
      // For now, we'll simulate creating a template
      // In a real implementation, this would call a backend endpoint
      return {
        ...template,
        id: `template_${Date.now()}`,
        createdAt: new Date().toISOString(),
      };
    } catch (error) {
      console.error("Error creating payment template:", error);
      throw new Error("Failed to create payment template");
    }
  }

  // Mock data generators for demonstration purposes
  private generateMockPaymentHistory(walletAddress: string, chainId?: number): PaymentHistoryItem[] {
    const tokens = ['ETH', 'USDC', 'DAI', 'USDT'];
    const statuses: ('pending' | 'confirmed' | 'failed')[] = ['confirmed', 'confirmed', 'confirmed', 'failed'];
    const recipients = [
      '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
      '0xAb5801a7D398351b8bE11C439e05C5B3259ffCF7',
      '0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520',
      '0x281055afc982d96fab65b3a49cac8b878184cb16'
    ];
    
    return Array.from({ length: 15 }, (_, i) => {
      const token = tokens[Math.floor(Math.random() * tokens.length)];
      const amount = (Math.random() * 10).toFixed(4);
      const status = statuses[Math.floor(Math.random() * statuses.length)];
      const recipient = recipients[Math.floor(Math.random() * recipients.length)];
      const txHash = `0x${Array.from({length: 64}, () => Math.floor(Math.random() * 16).toString(16)).join('')}`;
      
      return {
        id: `tx_${i}_${Date.now()}`,
        timestamp: new Date(Date.now() - i * 24 * 60 * 60 * 1000).toISOString(),
        amount,
        token,
        recipient,
        status,
        chainId: chainId || 1,
        transactionHash: status !== 'pending' ? txHash : undefined,
        gasUsed: status === 'confirmed' ? (Math.random() * 0.01).toFixed(6) : undefined,
        category: ['Payment', 'Transfer', 'Gift', 'Bill'][Math.floor(Math.random() * 4)],
        explorerUrl: status !== 'pending' ? `https://etherscan.io/tx/${txHash}` : undefined
      };
    });
  }

  private generateMockSpendingAnalytics(walletAddress: string, chainId?: number, period: 'week' | 'month' | 'year'): SpendingAnalytics {
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

  private generateMockRecipients(walletAddress: string): Recipient[] {
    return [
      {
        id: 'recipient_1',
        name: 'Alice',
        address: '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        lastUsed: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
        chainId: 1
      },
      {
        id: 'recipient_2',
        name: 'Bob',
        address: '0xAb5801a7D398351b8bE11C439e05C5B3259ffCF7',
        lastUsed: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
        chainId: 1
      },
      {
        id: 'recipient_3',
        name: 'Charlie',
        address: '0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520',
        lastUsed: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
        chainId: 534352 // Scroll
      }
    ];
  }

  private generateMockPaymentTemplates(walletAddress: string): PaymentTemplate[] {
    return [
      {
        id: 'template_1',
        name: 'Monthly Rent',
        amount: '1.5',
        token: 'ETH',
        recipient: '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        schedule: {
          frequency: 'monthly',
          dayOfMonth: 1
        },
        chainId: 1,
        createdAt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()
      },
      {
        id: 'template_2',
        name: 'Weekly Contribution',
        amount: '100',
        token: 'USDC',
        recipient: '0xAb5801a7D398351b8bE11C439e05C5B3259ffCF7',
        schedule: {
          frequency: 'weekly',
          dayOfWeek: 1 // Monday
        },
        chainId: 534352, // Scroll
        createdAt: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString()
      }
    ];
  }
}