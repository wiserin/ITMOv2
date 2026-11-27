import { AccountModal } from '../components/AccountModal';
import { AccountRow } from '../components/AccountRow';
import { BackLink } from '../components/BackLink';
import { useEffect, useState } from 'react';
import { api, ApiError, type AccountResponse } from '../api/client';
import {
    Button, Card, EmptyState,
    Feedback, Pagination, SearchField,
} from '../UI';

export function AdminPage({ onExpired }: { onExpired: () => void }) {
    const [query, setQuery] = useState('');
    const [offset, setOffset] = useState(0);
    const [accounts, setAccounts] = useState<AccountResponse[]>([]);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [selected, setSelected] = useState<AccountResponse | null>(
        null
    );
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
                const result = await api.find(
                    prefix, offset, controller.signal
                );
                if (!controller.signal.aborted) {
                    setAccounts(result.accounts);
                }
            } catch (reason) {
                if (controller.signal.aborted) return;
                if (reason instanceof ApiError
                    && reason.status === 401) {
                    onExpired();
                } else {
                    setError(reason instanceof Error
                        ? reason.message : 'Ошибка поиска.');
                }
            } finally {
                if (!controller.signal.aborted) setBusy(false);
            }
        }, 300);
        return () => { clearTimeout(timer); controller.abort(); };
    }, [prefix, offset, attempt, onExpired]);

    return <main className="am-page am-admin-page">
        <BackLink />
        <div className="am-page-heading">
            <div><p className="am-eyebrow">Управление сообществом</p>
                <h1>Admin Panel</h1></div>
            <span className="am-access-badge">
                Рабочее пространство
            </span>
        </div>
        <Card className="am-search-card">
            <div className="am-section-top"><h2>Пользователи</h2>
                <span className="am-muted">Поиск по username</span>
            </div>
            <SearchField label="Имя пользователя"
                placeholder="Начните вводить username…"
                maxLength={100}
                clearLabel="Очистить поиск" value={query}
                onChange={value => {
                    setQuery(value);
                    setOffset(0);
                }} />
            <p className="am-search-hint">
                Ищем по началу имени с учётом регистра.
            </p>
            <div className="am-search-results" aria-busy={busy}>
                {busy ? <EmptyState loading
                    title="Ищем пользователей…" />
                    : error ? <div className="am-search-error">
                        <Feedback>{error}</Feedback>
                        <Button onClick={() => {
                            setAttempt(value => value + 1);
                        }}>Повторить</Button>
                    </div> : accounts.length ? <>
                    <div className="am-results-caption">
                        Найденные аккаунты
                    </div>
                    <ul className="am-user-list">
                        {accounts.map(account => <li key={account.id}>
                            <AccountRow account={account}
                                onSelect={() => setSelected(account)}
                            />
                        </li>)}
                    </ul>
                </> : <EmptyState title={prefix
                    ? 'Пользователи не найдены'
                    : 'Кого будем искать?'}>
                    {prefix ? 'Попробуйте другой префикс имени.'
                        : 'Введите хотя бы один символ — '
                            + 'результаты появятся здесь.'}
                </EmptyState>}
            </div>
            {prefix && !busy && !error &&
                (offset > 0 || accounts.length === 20) &&
                <Pagination offset={offset} pageSize={20}
                    hasNext={accounts.length === 20 && offset < 10000}
                    onChange={setOffset} />}
        </Card>
        {selected && <AccountModal account={selected}
            onClose={() => setSelected(null)} />}
    </main>;
}
