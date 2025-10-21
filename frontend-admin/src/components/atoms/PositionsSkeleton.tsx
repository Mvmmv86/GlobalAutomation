/**
 * PositionsSkeleton Component
 *
 * Elegant skeleton loader for positions cards while data is being fetched.
 * Provides better UX than spinners by showing content structure.
 *
 * Features:
 * - Shimmer animation effect
 * - Matches actual PositionsCard layout
 * - Configurable number of items
 * - Accessible (aria-busy)
 */

import React from 'react'
import { Card, CardContent, CardHeader } from './Card'
import { cn } from '@/lib/utils'

interface PositionsSkeletonProps {
  count?: number
  className?: string
}

const SkeletonLine: React.FC<{ className?: string }> = ({ className }) => (
  <div
    className={cn(
      'animate-pulse bg-gradient-to-r from-gray-200 via-gray-300 to-gray-200 bg-[length:200%_100%]',
      'dark:from-gray-700 dark:via-gray-600 dark:to-gray-700',
      'rounded',
      className
    )}
    style={{
      animation: 'shimmer 2s infinite'
    }}
  />
)

export const PositionsSkeleton: React.FC<PositionsSkeletonProps> = ({
  count = 3,
  className
}) => {
  return (
    <div className={cn('space-y-4', className)} aria-busy="true" aria-label="Loading positions">
      <style>{`
        @keyframes shimmer {
          0% {
            background-position: -200% 0;
          }
          100% {
            background-position: 200% 0;
          }
        }
      `}</style>

      {Array.from({ length: count }).map((_, index) => (
        <Card key={index} className="overflow-hidden">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {/* Symbol skeleton */}
                <SkeletonLine className="h-6 w-24" />
                {/* Side badge skeleton */}
                <SkeletonLine className="h-5 w-16" />
              </div>
              {/* Status badge skeleton */}
              <SkeletonLine className="h-5 w-20" />
            </div>
          </CardHeader>

          <CardContent className="space-y-4">
            {/* Price info */}
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <SkeletonLine className="h-3 w-16" />
                <SkeletonLine className="h-6 w-20" />
              </div>
              <div className="space-y-2">
                <SkeletonLine className="h-3 w-20" />
                <SkeletonLine className="h-6 w-24" />
              </div>
              <div className="space-y-2">
                <SkeletonLine className="h-3 w-16" />
                <SkeletonLine className="h-6 w-20" />
              </div>
            </div>

            {/* Size and P&L */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <SkeletonLine className="h-3 w-12" />
                <SkeletonLine className="h-5 w-16" />
              </div>
              <div className="space-y-2">
                <SkeletonLine className="h-3 w-10" />
                <SkeletonLine className="h-5 w-20" />
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex gap-2 pt-2">
              <SkeletonLine className="h-9 flex-1" />
              <SkeletonLine className="h-9 flex-1" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

/**
 * PositionsTableSkeleton - For table view
 */
export const PositionsTableSkeleton: React.FC<{ rows?: number }> = ({ rows = 5 }) => {
  return (
    <div className="space-y-2" aria-busy="true" aria-label="Loading positions table">
      <style>{`
        @keyframes shimmer {
          0% {
            background-position: -200% 0;
          }
          100% {
            background-position: 200% 0;
          }
        }
      `}</style>

      {/* Table header */}
      <div className="flex gap-4 pb-2 border-b border-gray-200 dark:border-gray-700">
        <SkeletonLine className="h-4 w-20" />
        <SkeletonLine className="h-4 w-16" />
        <SkeletonLine className="h-4 w-24" />
        <SkeletonLine className="h-4 w-24" />
        <SkeletonLine className="h-4 w-20" />
        <SkeletonLine className="h-4 w-20" />
      </div>

      {/* Table rows */}
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="flex gap-4 py-3 border-b border-gray-100 dark:border-gray-800">
          <SkeletonLine className="h-5 w-20" />
          <SkeletonLine className="h-5 w-16" />
          <SkeletonLine className="h-5 w-24" />
          <SkeletonLine className="h-5 w-24" />
          <SkeletonLine className="h-5 w-20" />
          <SkeletonLine className="h-5 w-20" />
        </div>
      ))}
    </div>
  )
}

/**
 * PositionsCardCompactSkeleton - For compact card view
 */
export const PositionsCardCompactSkeleton: React.FC<{ count?: number }> = ({ count = 3 }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" aria-busy="true">
      <style>{`
        @keyframes shimmer {
          0% {
            background-position: -200% 0;
          }
          100% {
            background-position: 200% 0;
          }
        }
      `}</style>

      {Array.from({ length: count }).map((_, index) => (
        <Card key={index} className="p-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <SkeletonLine className="h-5 w-24" />
              <SkeletonLine className="h-4 w-16" />
            </div>
            <SkeletonLine className="h-8 w-full" />
            <div className="flex justify-between">
              <SkeletonLine className="h-4 w-16" />
              <SkeletonLine className="h-4 w-20" />
            </div>
          </div>
        </Card>
      ))}
    </div>
  )
}
