import React, { useState } from 'react'
import { Bell, X, CheckCircle, AlertTriangle, Info, AlertCircle, Filter, MoreVertical, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../atoms/Card'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../atoms/Tabs'
import { cn, formatDate } from '@/lib/utils'
import { useNotifications, Notification } from '@/hooks/useNotifications'

interface NotificationCenterProps {
  className?: string
}

const NotificationCenter: React.FC<NotificationCenterProps> = ({ className }) => {
  const [activeTab, setActiveTab] = useState<string>('all')
  const [showUnreadOnly, setShowUnreadOnly] = useState(false)

  // Use the backend-connected hook
  const {
    notifications,
    unreadCount,
    isLoading,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    clearAll,
    isMarkingAllAsRead,
    isClearing
  } = useNotifications({
    limit: 100,
    refetchInterval: 30000 // 30 seconds
  })

  // Filter notifications based on active tab and read status
  const filteredNotifications = notifications.filter((notification: Notification) => {
    let categoryMatch = activeTab === 'all'

    // Map tabs to categories
    if (activeTab === 'order') {
      categoryMatch = notification.category === 'order'
    } else if (activeTab === 'position') {
      // Positions tab includes position and bot categories
      categoryMatch = notification.category === 'position' || notification.category === 'bot'
    } else if (activeTab === 'system') {
      categoryMatch = notification.category === 'system'
    } else if (activeTab === 'market') {
      categoryMatch = notification.category === 'market'
    } else if (activeTab === 'alerts') {
      // Alerts tab includes price_alert and indicator categories
      categoryMatch = notification.category === 'price_alert' || notification.category === 'indicator'
    }

    const readMatch = !showUnreadOnly || !notification.read
    return categoryMatch && readMatch
  })

  // Count notifications by category
  const counts = {
    all: notifications.length,
    unread: unreadCount,
    order: notifications.filter((n: Notification) => n.category === 'order').length,
    // Positions includes position + bot
    position: notifications.filter((n: Notification) => n.category === 'position' || n.category === 'bot').length,
    system: notifications.filter((n: Notification) => n.category === 'system').length,
    market: notifications.filter((n: Notification) => n.category === 'market').length,
    // Alerts includes price_alert + indicator
    alerts: notifications.filter((n: Notification) => n.category === 'price_alert' || n.category === 'indicator').length
  }

  const getNotificationIcon = (type: Notification['type']) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-success" />
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-warning" />
      case 'error':
        return <AlertCircle className="h-4 w-4 text-destructive" />
      case 'info':
      default:
        return <Info className="h-4 w-4 text-blue-500" />
    }
  }

  const getNotificationColors = (type: Notification['type']) => {
    switch (type) {
      case 'success':
        return 'border-l-success bg-success/5'
      case 'warning':
        return 'border-l-warning bg-warning/5'
      case 'error':
        return 'border-l-destructive bg-destructive/5'
      case 'info':
      default:
        return 'border-l-blue-500 bg-blue-500/5'
    }
  }

  const NotificationItem: React.FC<{ notification: Notification }> = ({ notification }) => {
    const handleClick = () => {
      if (!notification.read) {
        markAsRead(notification.id)
      }
    }

    return (
      <div
        className={cn(
          "p-4 border-l-4 cursor-pointer transition-all hover:bg-muted/50",
          getNotificationColors(notification.type),
          !notification.read && "border-l-4"
        )}
        onClick={handleClick}
      >
        <div className="flex items-start justify-between space-x-3">
          <div className="flex items-start space-x-3 flex-1 min-w-0">
            {getNotificationIcon(notification.type)}

            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2">
                <h4 className={cn(
                  "text-sm font-medium truncate",
                  !notification.read && "font-semibold"
                )}>
                  {notification.title}
                </h4>
                {!notification.read && (
                  <div className="h-2 w-2 bg-primary rounded-full flex-shrink-0" />
                )}
              </div>

              <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                {notification.message}
              </p>

              <div className="flex items-center space-x-2 mt-2">
                <Badge variant="outline" className="text-xs">
                  {notification.category.toUpperCase().replace('_', ' ')}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {formatDate(notification.timestamp)}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-1 flex-shrink-0">
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={(e) => {
                e.stopPropagation()
                deleteNotification(notification.id)
              }}
            >
              <X className="h-3 w-3" />
            </Button>
            <Button variant="ghost" size="icon" className="h-6 w-6">
              <MoreVertical className="h-3 w-3" />
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <Card className={cn("w-full max-w-2xl", className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-2">
            <Bell className="h-5 w-5" />
            <span>Notifications</span>
            {unreadCount > 0 && (
              <Badge variant="destructive" className="text-xs">
                {unreadCount}
              </Badge>
            )}
          </CardTitle>

          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowUnreadOnly(!showUnreadOnly)}
              className={cn(showUnreadOnly && "bg-primary/10")}
            >
              <Filter className="h-4 w-4 mr-2" />
              {showUnreadOnly ? 'Show All' : 'Unread Only'}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => markAllAsRead()}
              disabled={isMarkingAllAsRead || unreadCount === 0}
            >
              {isMarkingAllAsRead ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : null}
              Mark All Read
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => clearAll()}
              disabled={isClearing || notifications.length === 0}
            >
              {isClearing ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : null}
              Clear All
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <div className="px-6 pb-4">
            <TabsList className="grid w-full grid-cols-6">
              <TabsTrigger value="all" className="text-xs">
                All ({counts.all})
              </TabsTrigger>
              <TabsTrigger value="order" className="text-xs">
                Orders ({counts.order})
              </TabsTrigger>
              <TabsTrigger value="position" className="text-xs">
                Positions ({counts.position})
              </TabsTrigger>
              <TabsTrigger value="system" className="text-xs">
                System ({counts.system})
              </TabsTrigger>
              <TabsTrigger value="market" className="text-xs">
                Market ({counts.market})
              </TabsTrigger>
              <TabsTrigger value="alerts" className="text-xs">
                Alerts ({counts.alerts})
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value={activeTab} className="mt-0">
            <div className="max-h-96 overflow-y-auto">
              {isLoading ? (
                <div className="p-8 text-center text-muted-foreground">
                  <Loader2 className="h-12 w-12 mx-auto mb-4 animate-spin opacity-50" />
                  <h3 className="font-medium mb-2">Loading notifications...</h3>
                </div>
              ) : filteredNotifications.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  <Bell className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <h3 className="font-medium mb-2">No notifications</h3>
                  <p className="text-sm">
                    {showUnreadOnly ? 'No unread notifications' : 'All caught up!'}
                  </p>
                </div>
              ) : (
                <div className="divide-y">
                  {filteredNotifications.map((notification: Notification) => (
                    <NotificationItem key={notification.id} notification={notification} />
                  ))}
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>

        {/* Summary Footer */}
        {filteredNotifications.length > 0 && (
          <div className="p-4 border-t bg-muted/30">
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>
                Showing {filteredNotifications.length} of {notifications.length} notifications
              </span>
              {unreadCount > 0 && (
                <span className="font-medium">
                  {unreadCount} unread
                </span>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export { NotificationCenter }
export type { NotificationCenterProps }
