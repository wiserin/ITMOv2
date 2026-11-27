import { AccountDetails } from '../components/AccountDetails';
import { BackLink } from '../components/BackLink';
import { useEffect, useState } from 'react';
import { api, ApiError, type AccountResponse } from '../api/client';
import { Button, Card, Feedback } from '../UI';

export function AccountPage({ onExpired }: {
    onExpired: () => void;
}) {
    const [account, setAccount] = useState<AccountResponse | null>(
        null
    );
    const [error, setError] = useState('');
    const [attempt, setAttempt] = useState(0);
    useEffect(() => {
        let active = true;
        setError('');
        api.me().then(data => { if (active) setAccount(data); })
            .catch(reason => {
                if (!active) return;
                if (reason instanceof ApiError
                    && reason.status === 401) {
                    onExpired();
                } else {
                    setError(reason instanceof Error
                        ? reason.message : 'Ошибка загрузки.');
                }
            });
        return () => { active = false; };
    }, [attempt, onExpired]);

    return <main className="am-page am-account-page">
        <BackLink />
        <p className="am-eyebrow">Личное пространство</p>
        <h1>Мой аккаунт</h1>
        <p className="am-muted">Ваш профиль в AnimeMap.</p>
        <Card className="am-profile-card">
            {error ? <div>
                <Feedback>{error}</Feedback>
                <Button
                    onClick={() => setAttempt(value => value + 1)}>
                    Повторить
                </Button>
            </div> : account ? <AccountDetails account={account} />
                : <p role="status">Загружаем профиль…</p>}
        </Card>
    </main>;
}
