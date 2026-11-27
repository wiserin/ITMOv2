import { useEffect, useState } from 'react';
import { api, ApiError, type AccountResponse } from '../api/client';
import { AccountDetails, BackLink, Button, Card, Feedback } from '../UI';

export function AccountPage({ onExpired }: { onExpired: () => void }) {
  const [account, setAccount] = useState<AccountResponse | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setError('');
    api.me().then(data => { if (active) setAccount(data); })
      .catch(reason => {
        if (!active) return;
        if (reason instanceof ApiError && reason.status === 401) {
          onExpired();
        } else setError(reason.message);
      });
    return () => { active = false; };
  }, [attempt, onExpired]);

  return <main className="page account-page">
    <BackLink />
    <p className="eyebrow">Личное пространство</p>
    <h1>Мой аккаунт</h1>
    <p className="muted">Ваш профиль в AnimeMap.</p>
    <Card className="profile-card">
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
