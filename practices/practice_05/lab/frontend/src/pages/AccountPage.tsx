import { useEffect, useState } from 'react';
import { api, ApiError, type AccountResponse } from '../api/client';
import { AccountDetails } from '../components/AccountDetails';

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
    <a className="back-link" href="#/">← На главную</a>
    <p className="eyebrow">Личное пространство</p>
    <h1>Мой аккаунт</h1>
    <p className="muted">Ваш профиль в AnimeMap.</p>
    <section className="card profile-card">
      {error ? <div role="alert">
        <p className="error">{error}</p>
        <button className="secondary"
          onClick={() => setAttempt(value => value + 1)}>
          Повторить
        </button>
      </div> : account ? <AccountDetails account={account} />
        : <p role="status">Загружаем профиль…</p>}
    </section>
  </main>;
}
