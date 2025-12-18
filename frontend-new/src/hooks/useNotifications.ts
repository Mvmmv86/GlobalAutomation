import { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'

// Types matching backend and NotificationCenter component
export interface Notification {
  id: string
  type: 'success' | 'warning' | 'error' | 'info'
  category: 'order' | 'position' | 'system' | 'market' | 'bot' | 'price_alert' | 'indicator'
  title: string
  message: string
  timestamp: string
  read: boolean
  actionUrl?: string
  metadata?: Record<string, any>
}

interface NotificationsResponse {
  success: boolean
  data: Notification[]
  total: number
  unread_count: number
}

interface NotificationCountResponse {
  success: boolean
  unread_count: number
  total_count: number
}

// Fetch notifications from API
const fetchNotifications = async (params: {
  category?: string
  unread_only?: boolean
  limit?: number
  offset?: number
}): Promise<NotificationsResponse> => {
  const queryParams = new URLSearchParams()
  if (params.category) queryParams.append('category', params.category)
  if (params.unread_only) queryParams.append('unread_only', 'true')
  if (params.limit) queryParams.append('limit', params.limit.toString())
  if (params.offset) queryParams.append('offset', params.offset.toString())

  const url = `/notifications${queryParams.toString() ? `?${queryParams.toString()}` : ''}`
  // Use axios instance directly to get full response (not just .data)
  const axios = apiClient.getAxiosInstance()
  const response = await axios.get<NotificationsResponse>(url)
  // Return full response data with success, data, total, unread_count
  return response.data || { success: true, data: [], total: 0, unread_count: 0 }
}

// Fetch notification count
const fetchNotificationCount = async (): Promise<NotificationCountResponse> => {
  // Use axios instance directly to get full response
  const axios = apiClient.getAxiosInstance()
  const response = await axios.get<NotificationCountResponse>('/notifications/count')
  // Return full response data with success, unread_count, total_count
  return response.data || { success: true, unread_count: 0, total_count: 0 }
}

// Mark notification as read
const markAsReadApi = async (notificationId: string): Promise<void> => {
  const axios = apiClient.getAxiosInstance()
  await axios.put(`/notifications/${notificationId}`, { read: true })
}

// Mark all notifications as read
const markAllAsReadApi = async (): Promise<void> => {
  const axios = apiClient.getAxiosInstance()
  await axios.put('/notifications/mark-all-read')
}

// Delete notification
const deleteNotificationApi = async (notificationId: string): Promise<void> => {
  const axios = apiClient.getAxiosInstance()
  await axios.delete(`/notifications/${notificationId}`)
}

// Clear all notifications
const clearAllNotificationsApi = async (): Promise<void> => {
  const axios = apiClient.getAxiosInstance()
  await axios.delete('/notifications')
}

// Hook options
interface UseNotificationsOptions {
  category?: string
  unreadOnly?: boolean
  limit?: number
  enabled?: boolean
  refetchInterval?: number
}

export function useNotifications(options: UseNotificationsOptions = {}) {
  const {
    category,
    unreadOnly = false,
    limit = 50,
    enabled = true,
    refetchInterval = 30000 // 30 seconds default
  } = options

  const queryClient = useQueryClient()

  // Query for notifications
  const {
    data: notificationsData,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: ['notifications', category, unreadOnly, limit],
    queryFn: () => fetchNotifications({
      category,
      unread_only: unreadOnly,
      limit
    }),
    enabled,
    refetchInterval,
    staleTime: 10000, // 10 seconds
  })

  // Query for unread count (separate for badge updates)
  const { data: countData } = useQuery({
    queryKey: ['notifications-count'],
    queryFn: fetchNotificationCount,
    enabled,
    refetchInterval: 15000, // 15 seconds
    staleTime: 5000, // 5 seconds
  })

  // Mutation for marking as read
  const markAsReadMutation = useMutation({
    mutationFn: markAsReadApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notifications-count'] })
    }
  })

  // Mutation for marking all as read
  const markAllAsReadMutation = useMutation({
    mutationFn: markAllAsReadApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notifications-count'] })
    }
  })

  // Mutation for deleting notification
  const deleteNotificationMutation = useMutation({
    mutationFn: deleteNotificationApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notifications-count'] })
    }
  })

  // Mutation for clearing all notifications
  const clearAllMutation = useMutation({
    mutationFn: clearAllNotificationsApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notifications-count'] })
    }
  })

  // Callbacks matching NotificationCenter props
  const markAsRead = useCallback((notificationId: string) => {
    markAsReadMutation.mutate(notificationId)
  }, [markAsReadMutation])

  const markAllAsRead = useCallback(() => {
    markAllAsReadMutation.mutate()
  }, [markAllAsReadMutation])

  const deleteNotification = useCallback((notificationId: string) => {
    deleteNotificationMutation.mutate(notificationId)
  }, [deleteNotificationMutation])

  const clearAll = useCallback(() => {
    clearAllMutation.mutate()
  }, [clearAllMutation])

  return {
    // Data
    notifications: notificationsData?.data || [],
    total: notificationsData?.total || 0,
    unreadCount: countData?.unread_count || 0,
    totalCount: countData?.total_count || 0,

    // Loading states
    isLoading,
    error,

    // Actions
    markAsRead,
    markAllAsRead,
    deleteNotification,
    clearAll,
    refetch,

    // Mutation states (for loading indicators)
    isMarkingAsRead: markAsReadMutation.isPending,
    isMarkingAllAsRead: markAllAsReadMutation.isPending,
    isDeleting: deleteNotificationMutation.isPending,
    isClearing: clearAllMutation.isPending,
  }
}

// Hook for just the notification count (badge)
export function useNotificationCount() {
  const { data, isLoading } = useQuery({
    queryKey: ['notifications-count'],
    queryFn: fetchNotificationCount,
    refetchInterval: 15000, // 15 seconds
    staleTime: 5000, // 5 seconds
  })

  return {
    unreadCount: data?.unread_count || 0,
    totalCount: data?.total_count || 0,
    isLoading
  }
}

export default useNotifications
