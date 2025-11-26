import React, { useState, useEffect } from 'react'
import { Bell, X, CheckCircle, AlertTriangle, Info, AlertCircle, Filter, MoreVertical } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../atoms/Card'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../atoms/Tabs'
import { cn, formatDate } from '@/lib/utils'

interface Notification {
  id: string
  type: 'success' | 'warning' | 'error' | 'info'
  title: string
  message: string
  timestamp: string
  read: boolean
  category: 'order' | 'position' | 'system' | 'market'
  actionUrl?: string
  metadata?: Record<string, any>
}

interface NotificationCenterProps {
  notifications: Notification[]
  onMarkAsRead: (notificationId: string) => void
  onMarkAllAsRead: () => void
  onDeleteNotification: (notificationId: string) => void
  onClearAll: () => void
  className?: string
}

const NotificationCenter: React.FC<NotificationCenterProps> = ({
  notifications,
  onMarkAsRead,
  onMarkAllAsRead,
  onDeleteNotification,
  onClearAll,
  className
}) => {
  const [activeTab, setActiveTab] = useState<string>('all')
  const [showUnreadOnly, setShowUnreadOnly] = useState(false)

  // Filter notifications based on active tab and read status
  const filteredNotifications = notifications.filter(notification => {
    const categoryMatch = activeTab === 'all' || notification.category === activeTab
    const readMatch = !showUnreadOnly || !notification.read
    return categoryMatch && readMatch
  })

  // Count notifications by category
  const counts = {
    all: notifications.length,
    unread: notifications.filter(n => !n.read).length,
    order: notifications.filter(n => n.category === 'order').length,
    position: notifications.filter(n => n.category === 'position').length,
    system: notifications.filter(n => n.category === 'system').length,
    market: notifications.filter(n => n.category === 'market').length
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
        onMarkAsRead(notification.id)
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
                  {notification.category.toUpperCase()}
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
                onDeleteNotification(notification.id)
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
            {counts.unread > 0 && (
              <Badge variant="destructive" className="text-xs">
                {counts.unread}
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

            <Button variant="outline" size="sm" onClick={onMarkAllAsRead}>
              Mark All Read
            </Button>

            <Button variant="outline" size="sm" onClick={onClearAll}>
              Clear All
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <div className="px-6 pb-4">
            <TabsList className="grid w-full grid-cols-5">
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
            </TabsList>
          </div>

          <TabsContent value={activeTab} className="mt-0">
            <div className="max-h-96 overflow-y-auto">
              {filteredNotifications.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  <Bell className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <h3 className="font-medium mb-2">No notifications</h3>
                  <p className="text-sm">
                    {showUnreadOnly ? 'No unread notifications' : 'All caught up!'}
                  </p>
                </div>
              ) : (
                <div className="divide-y">
                  {filteredNotifications.map((notification) => (
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
              {counts.unread > 0 && (
                <span className="font-medium">
                  {counts.unread} unread
                </span>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// Hook for managing notifications
export const useNotifications = () => {
  const [notifications, setNotifications] = useState<Notification[]>([])

  const addNotification = (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => {
    const newNotification: Notification = {
      ...notification,
      id: Date.now().toString(),
      timestamp: new Date().toISOString(),
      read: false
    }
    setNotifications(prev => [newNotification, ...prev])
  }

  const markAsRead = (notificationId: string) => {
    setNotifications(prev => 
      prev.map(n => n.id === notificationId ? { ...n, read: true } : n)
    )
  }

  const markAllAsRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })))
  }

  const deleteNotification = (notificationId: string) => {
    setNotifications(prev => prev.filter(n => n.id !== notificationId))
  }

  const clearAll = () => {
    setNotifications([])
  }

  return {
    notifications,
    addNotification,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    clearAll
  }
}

export { NotificationCenter }
export type { NotificationCenterProps, Notification }