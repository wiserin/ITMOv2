import { Spinner } from './Spinner';
import type { ReactNode } from 'react';

export function EmptyState({ title, children, loading = false }: {
  title: string;
  children?: ReactNode;
  loading?: boolean;
}) {
  return <div className="empty-state" role="status">
    {loading ? <Spinner /> : <>
      <span className="empty-symbol" aria-hidden="true">⌕</span>
      <h3>{title}</h3>
    </>}
    {loading ? title : <p>{children}</p>}
  </div>;
}
