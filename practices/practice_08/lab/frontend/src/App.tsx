import { BackLink } from './components/BackLink';
import { Header } from './components/Header';
import { useCallback, useEffect, useState } from 'react';
import { api, ApiError, canModerate } from './api/client';
import type { AccountResponse } from './api/client';
import { Button, Feedback, Spinner } from './UI';
import { AuthPage } from './pages/AuthPage';
import { HomePage } from './pages/HomePage';
import { AccountPage } from './pages/AccountPage';
import { AdminPage } from './pages/AdminPage';

function currentRoute() {
    return window.location.hash.slice(1) || window.location.pathname;
}

export function App() {
    const [route, setRoute] = useState(currentRoute);
    const [account, setAccount] = useState<AccountResponse | null>(
        null
    );
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [attempt, setAttempt] = useState(0);
    const onExpired = useCallback(() => {
        setAccount(null);
        window.location.hash = '/login';
    }, []);

    useEffect(() => {
        const change = () => setRoute(currentRoute());
        window.addEventListener('hashchange', change);
        return () => window.removeEventListener('hashchange', change);
    }, []);

    useEffect(() => {
        let active = true;
        setLoading(true);
        setError('');
        api.me().then(data => { if (active) setAccount(data); })
            .catch(reason => {
                if (!active) return;
                if (!(reason instanceof ApiError
                    && reason.status === 401)) {
                    setError(reason instanceof Error
                        ? reason.message : 'Ошибка загрузки.');
                }
            }).finally(() => { if (active) setLoading(false); });
        return () => { active = false; };
    }, [attempt]);

    useEffect(() => {
        if (loading || error) return;
        if (!account && !['/login', '/register'].includes(route)) {
            window.location.hash = '/login';
        }
        if (account && ['/login', '/register'].includes(route)) {
            window.location.hash = '/';
        }
    }, [loading, error, account, route]);

    if (loading) return <div className="am-app-status" role="status">
        <Spinner /> Загружаем AnimeMap…
    </div>;
    if (error) return <main className="am-app-status">
        <h1>Не удалось загрузить AnimeMap</h1>
        <Feedback>{error}</Feedback>
        <Button
            onClick={() => setAttempt(value => value + 1)}>
            Повторить
        </Button>
    </main>;
    if (!account) return <AuthPage register={route === '/register'}
        onLogin={setAccount} />;

    return <><Header account={account} />
        {route === '/account' ? <AccountPage onExpired={onExpired} />
            : route === '/admin' ? canModerate(account)
                ? <AdminPage onExpired={onExpired} />
                : <main className="am-page">
                    <BackLink /><h1>Доступ ограничен</h1>
                    <p>
                        Admin Panel доступна модераторам
                        и администраторам.
                    </p>
                </main>
                : <HomePage />}
    </>;
}
