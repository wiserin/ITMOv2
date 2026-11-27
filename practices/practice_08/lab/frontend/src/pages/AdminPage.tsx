import { useEffect, useState } from 'react';
import { api, ApiError, type AccountResponse } from '../api/client';
import {
  AccountModal, AccountRow, BackLink, Button, Card, EmptyState,
  Feedback, Pagination, SearchField,
} from '../UI';

export function AdminPage({ onExpired }: { onExpired: () => void }) {
  const [query, setQuery] = useState('');
  const [offset, setOffset] = useState(0);
  const [accounts, setAccounts] = useState<AccountResponse[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<AccountResponse | null>(null);
  const [attempt, setAttempt] = useState(0);
  const prefix = query.trim();

  useEffect(() => {
    const controller = new AbortController();
    setAccounts([]);
    setError('');
    if (!prefix) { setBusy(false); return; }
    setBusy(true);
    const timer = setTimeout(async () => {
      try {
        const result = await api.find(prefix, offset, controller.signal);
        if (!controller.signal.aborted) setAccounts(result.accounts);
      } catch (reason) {
        if (controller.signal.aborted) return;
        if (reason instanceof ApiError && reason.status === 401) {
          onExpired();
        } else {
          setError(reason instanceof Error ? reason.message : 'Ошибка поиска.');
        }
      } finally {
        if (!controller.signal.aborted) setBusy(false);
      }
    }, 300);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [prefix, offset, attempt, onExpired]);

  return <main className="page admin-page">
    <BackLink />
    <div className="page-heading">
      <div><p className="eyebrow">Управление сообществом</p>
        <h1>Admin Panel</h1></div>
      <span className="access-badge">Рабочее пространство</span>
    </div>
    <Card className="search-card">
      <div className="section-top"><h2>Пользователи</h2>
        <span className="muted">Поиск по username</span></div>
      <SearchField value={query} onChange={value => {
        setQuery(value);
        setOffset(0);
      }} />
      <p className="search-hint">Ищем по началу имени с учётом регистра.</p>
      <div className="search-results" aria-busy={busy}>
        {busy ? <EmptyState loading title="Ищем пользователей…" />
          : error ? <div className="empty-state">
          <Feedback>{error}</Feedback>
          <Button
            onClick={() => setAttempt(value => value + 1)}>Повторить</Button>
        </div> : accounts.length ? <>
          <div className="results-caption">Найденные аккаунты</div>
          <ul className="user-list">
            {accounts.map(account => <li key={account.id}>
              <AccountRow account={account}
                onSelect={() => setSelected(account)} />
            </li>)}
          </ul>
        </> : <EmptyState title={prefix
          ? 'Пользователи не найдены' : 'Кого будем искать?'}>
          {prefix ? 'Попробуйте другой префикс имени.'
            : 'Введите хотя бы один символ — результаты появятся здесь.'}
        </EmptyState>}
      </div>
      {prefix && !busy && !error &&
        (offset > 0 || accounts.length === 20) &&
        <Pagination offset={offset} count={accounts.length}
          onChange={setOffset} />}
    </Card>
    {selected && <AccountModal account={selected}
      onClose={() => setSelected(null)} />}
  </main>;
}
