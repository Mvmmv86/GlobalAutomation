import { cn } from '@/lib/utils'
import { cva, type VariantProps } from 'class-variance-authority'

const spinnerVariants = cva(
  'animate-spin rounded-full border-solid border-current border-r-transparent',
  {
    variants: {
      size: {
        sm: 'h-4 w-4 border-2',
        md: 'h-6 w-6 border-2',
        lg: 'h-8 w-8 border-3',
        xl: 'h-12 w-12 border-4',
      },
      variant: {
        default: 'text-primary',
        secondary: 'text-secondary',
        muted: 'text-muted-foreground',
      },
    },
    defaultVariants: {
      size: 'md',
      variant: 'default',
    },
  }
)

interface LoadingSpinnerProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof spinnerVariants> {
  text?: string
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  className,
  size,
  variant,
  text,
  ...props
}) => {
  return (
    <div className={cn('flex items-center gap-2', className)} {...props}>
      <div className={cn(spinnerVariants({ size, variant }))} />
      {text && <span className="text-sm text-muted-foreground">{text}</span>}
    </div>
  )
}