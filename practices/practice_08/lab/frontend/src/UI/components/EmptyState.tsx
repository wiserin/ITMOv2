import type { ReactNode } from 'react';
import { Spinner } from './Spinner';

export function EmptyState({
    title, children, loading = false, symbol = '⌕',
}: {
    title: string;
    children?: ReactNode;
    loading?: boolean;
    symbol?: ReactNode;
}) {
    return <div className="ui-empty" role="status">
        {loading ? <Spinner /> : <>
            <span className="ui-empty__symbol" aria-hidden="true">
                {symbol}
            </span>
            <h3>{title}</h3>
        </>}
        {loading ? title : <p>{children}</p>}
    </div>;
}
