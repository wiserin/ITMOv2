import { useEffect, useState } from 'react';
import { api, ApiError, type AccountResponse } from '../api/client';
import { Avatar, roleNames } from '../components/AccountDetails';
import { AccountModal } from '../components/AccountModal';

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
    <a className="back-link" href="#/">← На главную</a>
    <div className="page-heading">
      <div><p className="eyebrow">Управление сообществом</p>
        <h1>Admin Panel</h1></div>
      <span className="access-badge">Рабочее пространство</span>
    </div>
    <section className="card search-card">
      <div className="section-top"><h2>Пользователи</h2>
        <span className="muted">Поиск по username</span></div>
      <label className="search-label" htmlFor="user-search">
        Имя пользователя
      </label>
      <div className="search-input">
        <span aria-hidden="true">⌕</span>
        <input id="user-search" value={query} maxLength={100}
          autoComplete="off" placeholder="Начните вводить username…"
          onChange={event => {
            setQuery(event.target.value);
            setOffset(0);
          }} />
        {query && <button className="icon-button"
          aria-label="Очистить поиск"
          onClick={() => { setQuery(''); setOffset(0); }}>×</button>}
      </div>
      <p className="search-hint">Ищем по началу имени с учётом регистра.</p>
      <div className="search-results" aria-busy={busy}>
        {busy ? <div className="empty-state" role="status">
          <span className="spinner" /> Ищем пользователей…
        </div> : error ? <div className="empty-state" role="alert">
          <p className="error">{error}</p>
          <button className="secondary"
            onClick={() => setAttempt(value => value + 1)}>Повторить</button>
        </div> : accounts.length ? <>
          <div className="results-caption">Найденные аккаунты</div>
          <ul className="user-list">
            {accounts.map(account => <li key={account.id}>
              <button className="user-row"
                onClick={() => setSelected(account)}>
                <Avatar account={account} />
                <span className="user-info">
                  <strong>{account.display_name || account.username}</strong>
                  <span>@{account.username} · {account.email}</span>
                </span>
                <span className={`role-badge ${account.role}`}>
                  {roleNames[account.role]}</span>
                <span className="row-arrow" aria-hidden="true">↗</span>
              </button>
            </li>)}
          </ul>
        </> : <div className="empty-state" role="status">
          <span className="empty-symbol" aria-hidden="true">⌕</span>
          <h3>{prefix ? 'Пользователи не найдены' : 'Кого будем искать?'}</h3>
          <p>{prefix ? 'Попробуйте другой префикс имени.'
            : 'Введите хотя бы один символ — результаты появятся здесь.'}</p>
        </div>}
      </div>
      {prefix && !busy && !error &&
        (offset > 0 || accounts.length === 20) &&
        <div className="pagination">
          <button className="secondary" disabled={offset === 0}
            onClick={() => setOffset(value => value - 20)}>← Назад</button>
          <span>Страница {offset / 20 + 1}</span>
          <button className="secondary"
            disabled={accounts.length < 20 || offset >= 10000}
            onClick={() => setOffset(value => value + 20)}>Далее →</button>
        </div>}
    </section>
    {selected && <AccountModal account={selected}
      onClose={() => setSelected(null)} />}
  </main>;
}
