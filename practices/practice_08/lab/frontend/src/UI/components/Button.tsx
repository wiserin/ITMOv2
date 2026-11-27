import type { ComponentProps } from 'react';
import { Spinner } from './Spinner';

export type ButtonProps = ComponentProps<'button'> & {
    variant?: 'primary' | 'secondary' | 'icon' | 'plain';
    loading?: boolean;
};

export function Button({
    variant = 'secondary', className = '', type = 'button',
    loading = false, disabled, children, ...props
}: ButtonProps) {
    return <button {...props} type={type}
        className={`ui-button ui-button--${variant} ${className}`}
        disabled={disabled || loading}
        aria-busy={loading || props['aria-busy']}>
        {loading && <Spinner />}
        {children}
    </button>;
}
