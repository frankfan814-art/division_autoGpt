/**
 * Button component - 优化的按钮组件
 */

import { ButtonHTMLAttributes, forwardRef } from 'react';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'warning' | 'ghost' | 'success';
  size?: 'xs' | 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  fullWidth?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      isLoading,
      disabled,
      children,
      className = '',
      fullWidth = false,
      leftIcon,
      rightIcon,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center gap-2 font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]';

    const variantStyles = {
      primary:
        'bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800 focus:ring-primary-500 shadow-medium hover:shadow-large',
      secondary:
        'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 active:bg-gray-300 dark:active:bg-gray-600 focus:ring-gray-500',
      danger:
        'bg-danger-500 text-white hover:bg-danger-600 active:bg-danger-700 focus:ring-danger-500 shadow-medium hover:shadow-large',
      warning:
        'bg-warning-500 text-white hover:bg-warning-600 active:bg-warning-700 focus:ring-warning-500 shadow-medium hover:shadow-large',
      ghost:
        'bg-transparent text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 active:bg-gray-200 dark:active:bg-gray-700 focus:ring-gray-500',
      success:
        'bg-success-500 text-white hover:bg-success-600 active:bg-success-700 focus:ring-success-500 shadow-medium hover:shadow-large',
    };

    const sizeStyles = {
      xs: 'px-2.5 py-1 text-xs rounded-md',
      sm: 'px-3 py-1.5 text-sm rounded-lg',
      md: 'px-4 py-2 text-sm rounded-lg',
      lg: 'px-6 py-3 text-base rounded-xl',
    };

    const loadingSpinner = (
      <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
    );

    return (
      <button
        ref={ref}
        className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${
          fullWidth ? 'w-full' : ''
        } ${className}`}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && loadingSpinner}
        {!isLoading && leftIcon && <span className="flex-shrink-0">{leftIcon}</span>}
        {typeof children === 'string' ? <span>{children}</span> : children}
        {!isLoading && rightIcon && <span className="flex-shrink-0">{rightIcon}</span>}
      </button>
    );
  }
);

Button.displayName = 'Button';
