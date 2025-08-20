import axios from 'axios';
import { TradingError, ErrorCategory } from './error-handling';

export interface NotificationConfig {
  discord?: {
    webhookUrl: string;
    enabled: boolean;
    mentionRoles?: string[]; // Role IDs to mention
  };
  slack?: {
    webhookUrl: string;
    enabled: boolean;
    channel?: string;
    mentionUsers?: string[]; // User IDs to mention
  };
  email?: {
    enabled: boolean;
    smtpHost: string;
    smtpPort: number;
    smtpUser: string;
    smtpPassword: string;
    from: string;
    to: string[];
  };
  defaultEnabled: boolean;
  rateLimitMinutes: number; // Prevent spam
}

export interface AlertLevel {
  level: 'info' | 'warning' | 'error' | 'critical';
  color: number; // Discord embed color
  emoji: string;
  shouldNotify: boolean;
}

export interface Alert {
  id: string;
  level: AlertLevel['level'];
  title: string;
  message: string;
  context?: Record<string, any>;
  timestamp: Date;
  service: string;
  environment: string;
  errorCategory?: ErrorCategory;
  accountId?: string;
  userId?: string;
}

export interface NotificationStats {
  totalSent: number;
  sentByLevel: Record<string, number>;
  sentByService: Record<string, number>;
  lastSent: Date | null;
  rateLimitedCount: number;
}

/**
 * Centralized notification system for alerts and monitoring
 */
export class NotificationService {
  private config: NotificationConfig;
  private stats: NotificationStats;
  private lastSentTimes: Map<string, Date> = new Map();

  constructor(config: NotificationConfig) {
    this.config = config;
    this.stats = {
      totalSent: 0,
      sentByLevel: {},
      sentByService: {},
      lastSent: null,
      rateLimitedCount: 0
    };
  }

  /**
   * Send alert notification to configured channels
   */
  async sendAlert(alert: Alert): Promise<boolean> {
    if (!this.config.defaultEnabled) {
      return false;
    }

    // Check rate limiting
    if (this.isRateLimited(alert)) {
      this.stats.rateLimitedCount++;
      console.log(`Alert rate limited: ${alert.id}`);
      return false;
    }

    const alertLevel = this.getAlertLevel(alert.level);
    
    if (!alertLevel.shouldNotify) {
      return false;
    }

    let success = false;

    // Send to Discord
    if (this.config.discord?.enabled) {
      try {
        await this.sendDiscordNotification(alert, alertLevel);
        success = true;
      } catch (error) {
        console.error('Discord notification failed:', error);
      }
    }

    // Send to Slack
    if (this.config.slack?.enabled) {
      try {
        await this.sendSlackNotification(alert, alertLevel);
        success = true;
      } catch (error) {
        console.error('Slack notification failed:', error);
      }
    }

    // Send to Email
    if (this.config.email?.enabled) {
      try {
        await this.sendEmailNotification(alert, alertLevel);
        success = true;
      } catch (error) {
        console.error('Email notification failed:', error);
      }
    }

    if (success) {
      this.updateStats(alert);
      this.lastSentTimes.set(this.getRateLimitKey(alert), new Date());
    }

    return success;
  }

  /**
   * Send Discord notification
   */
  private async sendDiscordNotification(alert: Alert, level: AlertLevel): Promise<void> {
    if (!this.config.discord?.webhookUrl) {
      throw new Error('Discord webhook URL not configured');
    }

    const mentions = this.config.discord.mentionRoles?.map(role => `<@&${role}>`).join(' ') || '';
    
    const embed = {
      title: `${level.emoji} ${alert.title}`,
      description: alert.message,
      color: level.color,
      fields: [
        {
          name: 'Service',
          value: alert.service,
          inline: true
        },
        {
          name: 'Environment',
          value: alert.environment,
          inline: true
        },
        {
          name: 'Level',
          value: alert.level.toUpperCase(),
          inline: true
        },
        {
          name: 'Timestamp',
          value: alert.timestamp.toISOString(),
          inline: false
        }
      ],
      footer: {
        text: `Alert ID: ${alert.id}`
      }
    };

    // Add context fields if available
    if (alert.context) {
      for (const [key, value] of Object.entries(alert.context)) {
        if (embed.fields.length < 25) { // Discord limit
          embed.fields.push({
            name: this.capitalizeFirst(key),
            value: String(value),
            inline: true
          });
        }
      }
    }

    const payload = {
      content: level.level === 'critical' ? mentions : undefined,
      embeds: [embed]
    };

    await axios.post(this.config.discord.webhookUrl, payload);
  }

  /**
   * Send Slack notification
   */
  private async sendSlackNotification(alert: Alert, level: AlertLevel): Promise<void> {
    if (!this.config.slack?.webhookUrl) {
      throw new Error('Slack webhook URL not configured');
    }

    const mentions = this.config.slack.mentionUsers?.map(user => `<@${user}>`).join(' ') || '';
    
    const attachment = {
      color: this.getSlackColor(level.level),
      title: `${level.emoji} ${alert.title}`,
      text: alert.message,
      fields: [
        {
          title: 'Service',
          value: alert.service,
          short: true
        },
        {
          title: 'Environment',
          value: alert.environment,
          short: true
        },
        {
          title: 'Level',
          value: alert.level.toUpperCase(),
          short: true
        },
        {
          title: 'Time',
          value: alert.timestamp.toISOString(),
          short: true
        }
      ],
      footer: `Alert ID: ${alert.id}`,
      ts: Math.floor(alert.timestamp.getTime() / 1000)
    };

    // Add context fields
    if (alert.context) {
      for (const [key, value] of Object.entries(alert.context)) {
        if (attachment.fields.length < 20) { // Slack best practice
          attachment.fields.push({
            title: this.capitalizeFirst(key),
            value: String(value),
            short: true
          });
        }
      }
    }

    const payload = {
      channel: this.config.slack.channel,
      text: level.level === 'critical' ? mentions : undefined,
      attachments: [attachment]
    };

    await axios.post(this.config.slack.webhookUrl, payload);
  }

  /**
   * Send email notification (placeholder - would need email service)
   */
  private async sendEmailNotification(alert: Alert, level: AlertLevel): Promise<void> {
    // This would require implementing nodemailer or similar
    console.log('Email notification would be sent:', {
      to: this.config.email?.to,
      subject: `${level.emoji} ${alert.title}`,
      alert
    });
  }

  /**
   * Create alert from trading error
   */
  createErrorAlert(
    error: TradingError,
    service: string,
    environment: string = 'production'
  ): Alert {
    const level = this.mapErrorCategoryToLevel(error.category);
    
    return {
      id: `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      level,
      title: `Trading Error: ${error.category}`,
      message: error.message,
      context: {
        errorCategory: error.category,
        stack: error.stack?.split('\n').slice(0, 3).join('\n'), // First 3 lines
        ...(error.context || {}),
        ...(error.accountId && { accountId: error.accountId }),
        ...(error.alertId && { alertId: error.alertId })
      },
      timestamp: error.timestamp || new Date(),
      service,
      environment,
      errorCategory: error.category,
      accountId: error.accountId,
      userId: error.context?.userId
    };
  }

  /**
   * Create system health alert
   */
  createHealthAlert(
    healthCheck: string,
    status: 'healthy' | 'degraded' | 'unhealthy',
    details: Record<string, any>,
    service: string,
    environment: string = 'production'
  ): Alert {
    const level = status === 'healthy' ? 'info' : status === 'degraded' ? 'warning' : 'error';
    
    return {
      id: `health_${healthCheck}_${Date.now()}`,
      level,
      title: `Health Check: ${healthCheck}`,
      message: `Service ${service} is ${status}`,
      context: details,
      timestamp: new Date(),
      service,
      environment
    };
  }

  /**
   * Create business metrics alert
   */
  createMetricsAlert(
    metric: string,
    value: number,
    threshold: number,
    comparison: 'above' | 'below',
    service: string,
    environment: string = 'production'
  ): Alert {
    const isThresholdBreached = comparison === 'above' ? value > threshold : value < threshold;
    const level = isThresholdBreached ? 'warning' : 'info';
    
    return {
      id: `metrics_${metric}_${Date.now()}`,
      level,
      title: `Metrics Alert: ${metric}`,
      message: `${metric} is ${value} (threshold: ${comparison} ${threshold})`,
      context: {
        metric,
        currentValue: value,
        threshold,
        comparison,
        breached: isThresholdBreached
      },
      timestamp: new Date(),
      service,
      environment
    };
  }

  /**
   * Get notification statistics
   */
  getStats(): NotificationStats {
    return { ...this.stats };
  }

  /**
   * Reset statistics
   */
  resetStats(): void {
    this.stats = {
      totalSent: 0,
      sentByLevel: {},
      sentByService: {},
      lastSent: null,
      rateLimitedCount: 0
    };
  }

  /**
   * Check if alert is rate limited
   */
  private isRateLimited(alert: Alert): boolean {
    const key = this.getRateLimitKey(alert);
    const lastSent = this.lastSentTimes.get(key);
    
    if (!lastSent) {
      return false;
    }

    const minutesSinceLastSent = (Date.now() - lastSent.getTime()) / (1000 * 60);
    return minutesSinceLastSent < this.config.rateLimitMinutes;
  }

  /**
   * Generate rate limit key for alert
   */
  private getRateLimitKey(alert: Alert): string {
    // Group similar alerts together for rate limiting
    return `${alert.service}_${alert.level}_${alert.errorCategory || 'general'}`;
  }

  /**
   * Update notification statistics
   */
  private updateStats(alert: Alert): void {
    this.stats.totalSent++;
    this.stats.sentByLevel[alert.level] = (this.stats.sentByLevel[alert.level] || 0) + 1;
    this.stats.sentByService[alert.service] = (this.stats.sentByService[alert.service] || 0) + 1;
    this.stats.lastSent = new Date();
  }

  /**
   * Get alert level configuration
   */
  private getAlertLevel(level: AlertLevel['level']): AlertLevel {
    const levels: Record<AlertLevel['level'], AlertLevel> = {
      info: {
        level: 'info',
        color: 0x3498db, // Blue
        emoji: 'ℹ️',
        shouldNotify: false
      },
      warning: {
        level: 'warning',
        color: 0xf39c12, // Orange
        emoji: '⚠️',
        shouldNotify: true
      },
      error: {
        level: 'error',
        color: 0xe74c3c, // Red
        emoji: '❌',
        shouldNotify: true
      },
      critical: {
        level: 'critical',
        color: 0x8b0000, // Dark red
        emoji: '🚨',
        shouldNotify: true
      }
    };

    return levels[level];
  }

  /**
   * Map error category to alert level
   */
  private mapErrorCategoryToLevel(category: ErrorCategory): AlertLevel['level'] {
    const criticalCategories = [
      ErrorCategory.SYSTEM_ERROR,
      ErrorCategory.DATABASE_ERROR
    ];

    const errorCategories = [
      ErrorCategory.AUTHENTICATION_ERROR,
      ErrorCategory.ACCOUNT_NOT_FOUND,
      ErrorCategory.INSUFFICIENT_BALANCE,
      ErrorCategory.EXCHANGE_REJECTED
    ];

    const warningCategories = [
      ErrorCategory.NETWORK_ERROR,
      ErrorCategory.TIMEOUT,
      ErrorCategory.RATE_LIMIT,
      ErrorCategory.PRICE_FEED_ERROR
    ];

    if (criticalCategories.includes(category)) {
      return 'critical';
    } else if (errorCategories.includes(category)) {
      return 'error';
    } else if (warningCategories.includes(category)) {
      return 'warning';
    } else {
      return 'info';
    }
  }

  /**
   * Get Slack color for alert level
   */
  private getSlackColor(level: AlertLevel['level']): string {
    const colors = {
      info: '#3498db',
      warning: '#f39c12',
      error: '#e74c3c',
      critical: '#8b0000'
    };
    return colors[level];
  }

  /**
   * Capitalize first letter of string
   */
  private capitalizeFirst(str: string): string {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }
}

/**
 * Global notification service instance
 */
let globalNotificationService: NotificationService | null = null;

export function initializeNotifications(config: NotificationConfig): NotificationService {
  globalNotificationService = new NotificationService(config);
  return globalNotificationService;
}

export function getNotificationService(): NotificationService {
  if (!globalNotificationService) {
    throw new Error('Notification service not initialized. Call initializeNotifications() first.');
  }
  return globalNotificationService;
}

/**
 * Utility functions for quick notifications
 */
export const NotificationUtils = {
  /**
   * Send critical error notification
   */
  async criticalError(
    title: string,
    message: string,
    service: string,
    context?: Record<string, any>
  ): Promise<boolean> {
    const notification = getNotificationService();
    const alert: Alert = {
      id: `critical_${Date.now()}`,
      level: 'critical',
      title,
      message,
      context,
      timestamp: new Date(),
      service,
      environment: process.env.NODE_ENV || 'development'
    };
    return notification.sendAlert(alert);
  },

  /**
   * Send warning notification
   */
  async warning(
    title: string,
    message: string,
    service: string,
    context?: Record<string, any>
  ): Promise<boolean> {
    const notification = getNotificationService();
    const alert: Alert = {
      id: `warning_${Date.now()}`,
      level: 'warning',
      title,
      message,
      context,
      timestamp: new Date(),
      service,
      environment: process.env.NODE_ENV || 'development'
    };
    return notification.sendAlert(alert);
  },

  /**
   * Send info notification
   */
  async info(
    title: string,
    message: string,
    service: string,
    context?: Record<string, any>
  ): Promise<boolean> {
    const notification = getNotificationService();
    const alert: Alert = {
      id: `info_${Date.now()}`,
      level: 'info',
      title,
      message,
      context,
      timestamp: new Date(),
      service,
      environment: process.env.NODE_ENV || 'development'
    };
    return notification.sendAlert(alert);
  }
};