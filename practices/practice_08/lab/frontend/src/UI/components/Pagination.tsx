import { Button } from './Button';

export function Pagination({ offset, count, onChange }: {
  offset: number;
  count: number;
  onChange: (offset: number) => void;
}) {
  return <div className="pagination">
    <Button disabled={offset === 0}
      onClick={() => onChange(offset - 20)}>← Назад</Button>
    <span>Страница {offset / 20 + 1}</span>
    <Button disabled={count < 20 || offset >= 10000}
      onClick={() => onChange(offset + 20)}>Далее →</Button>
  </div>;
}
