import { useId } from 'react';
import { Button } from './Button';

export function SearchField({ value, onChange }: {
  value: string;
  onChange: (value: string) => void;
}) {
  const id = useId();
  return <>
    <label className="search-label" htmlFor={id}>
      Имя пользователя
    </label>
    <div className="search-input">
      <span aria-hidden="true">⌕</span>
      <input id={id} value={value} maxLength={100}
        autoComplete="off" placeholder="Начните вводить username…"
        onChange={event => onChange(event.target.value)} />
      {value && <Button variant="icon" aria-label="Очистить поиск"
        onClick={() => onChange('')}>×</Button>}
    </div>
  </>;
}
