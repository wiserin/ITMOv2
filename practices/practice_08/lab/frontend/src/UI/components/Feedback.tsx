import type { ReactNode } from 'react';

export function Feedback({ children, variant = 'error' }: {
  children: ReactNode;
  variant?: 'error' | 'success';
}) {
  return <p className={variant}
    role={variant === 'error' ? 'alert' : 'status'}>{children}</p>;
}
