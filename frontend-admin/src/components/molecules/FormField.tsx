import React from 'react'
import { Label } from '../atoms/Label'
import { Input, InputProps } from '../atoms/Input'
import { cn } from '@/lib/utils'

interface FormFieldProps extends InputProps {
  label: string
  error?: string
  hint?: string
  required?: boolean
  className?: string
}

const FormField = React.forwardRef<HTMLInputElement, FormFieldProps>(
  ({ label, error, hint, required, className, id, ...props }, ref) => {
    const fieldId = id || `field-${label.toLowerCase().replace(/\s+/g, '-')}`

    return (
      <div className={cn("space-y-2", className)}>
        <Label htmlFor={fieldId} className={cn(required && "after:content-['*'] after:text-destructive after:ml-1")}>
          {label}
        </Label>
        
        <Input
          id={fieldId}
          ref={ref}
          className={cn(
            error && "border-destructive focus-visible:ring-destructive"
          )}
          {...props}
        />
        
        {(error || hint) && (
          <div className="space-y-1">
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
            {hint && !error && (
              <p className="text-sm text-muted-foreground">{hint}</p>
            )}
          </div>
        )}
      </div>
    )
  }
)

FormField.displayName = 'FormField'

export { FormField }
export type { FormFieldProps }