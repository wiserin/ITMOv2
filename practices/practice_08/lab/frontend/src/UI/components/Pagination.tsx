import { Button } from './Button';

type Availability =
    | { hasNext: boolean; totalCount?: never }
    | { totalCount: number; hasNext?: never };

export type PaginationProps = Availability & {
    offset: number;
    pageSize: number;
    onChange: (offset: number) => void;
    label?: string;
    previousLabel?: string;
    nextLabel?: string;
};

export function Pagination({
    offset, pageSize, hasNext, totalCount, onChange,
    label = 'Пагинация', previousLabel = '← Назад',
    nextLabel = 'Далее →',
}: PaginationProps) {
    const valid = Number.isInteger(pageSize) && pageSize > 0
        && Number.isInteger(offset) && offset >= 0;
    const next = valid && (hasNext
        ?? offset + pageSize < (totalCount ?? 0));
    return <nav className="ui-pagination" aria-label={label}>
        <Button disabled={!valid || offset === 0}
            onClick={() => onChange(Math.max(0, offset - pageSize))}>
            {previousLabel}
        </Button>
        <span aria-live="polite">
            Страница {valid ? Math.floor(offset / pageSize) + 1 : 1}
        </span>
        <Button disabled={!next}
            onClick={() => onChange(offset + pageSize)}>
            {nextLabel}
        </Button>
    </nav>;
}
