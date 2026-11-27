import type { ComponentProps } from 'react';

export function Card({
  className = '', ...props
}: ComponentProps<'section'>) {
  const classes = `card ${className}`.trim();
  return <section className={classes} {...props} />;
}
