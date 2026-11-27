import type { ComponentProps } from 'react';

type ButtonProps = ComponentProps<'button'> & {
  variant?: 'primary' | 'secondary' | 'icon' | 'plain';
};

export function Button({
  variant = 'secondary', className = '', type = 'button', ...props
}: ButtonProps) {
  const style = variant === 'icon' ? 'icon-button'
    : variant === 'plain' ? '' : variant;
  const classes = `${style} ${className}`.trim();
  return <button type={type} className={classes} {...props} />;
}
