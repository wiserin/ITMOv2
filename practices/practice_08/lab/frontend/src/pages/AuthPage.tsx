import { useState, type FormEvent } from 'react';
import { api, ApiError, type AccountResponse } from '../api/client';
import {
  AuthStory, AuthTabs, Button, Feedback, TextField,
} from '../UI';

export function AuthPage({ register, onLogin }: {
  register: boolean;
  onLogin: (account: AccountResponse) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [email, setEmail] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get('password') || '');
    const normalizedEmail = email.trim().toLowerCase();
    setBusy(true);
    setError('');
    try {
      if (register) {
        const username = String(form.get('username') || '').trim();
        if (!username) throw new Error('Введите имя пользователя.');
        await api.register({
          email: normalizedEmail,
          password,
          username,
          display_name:
            String(form.get('display_name') || '').trim() || null,
        });
        setSuccess(true);
        window.location.hash = '/login';
      } else {
        await api.login({ email: normalizedEmail, password });
        onLogin(await api.me());
        window.location.hash = '/';
      }
    } catch (reason) {
      setError(reason instanceof ApiError && reason.status === 401
        ? 'Неверный email или пароль, либо аккаунт неактивен.'
        : reason instanceof Error ? reason.message : 'Ошибка запроса.');
    } finally {
      setBusy(false);
    }
  }

  return <main className="auth-layout">
    <AuthStory />
    <section className="auth-form-side">
      <div className="auth-box">
        <AuthTabs register={register} onLogin={() => setError('')}
          onRegister={() => { setError(''); setSuccess(false); }} />
        <p className="eyebrow">Добро пожаловать в AnimeMap</p>
        <h2>{register ? 'Начнём путешествие' : 'С возвращением'}</h2>
        <p className="muted auth-intro">{register
          ? 'Создайте аккаунт для своих будущих открытий.'
          : 'Войдите, чтобы быть ближе к любимым историям.'}</p>
        {success && !register && <Feedback variant="success">
          Аккаунт создан. Войдите с вашим email и паролем.
        </Feedback>}
        <form onSubmit={submit} key={String(register)}>
          <fieldset disabled={busy}>
            {register && <>
              <TextField label="Имя пользователя" name="username"
                required maxLength={100}
                  autoComplete="username" placeholder="anime-fan" />
              <TextField label="Отображаемое имя" hint="необязательно"
                name="display_name" maxLength={100}
                autoComplete="nickname"
                placeholder="Как вас называть?" />
            </>}
            <TextField label="Email" name="email"
              type="email" required
                maxLength={254} autoComplete="email"
                value={email} onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com" />
            <TextField label="Пароль" name="password"
              type="password" required
              autoComplete={register
                ? 'new-password' : 'current-password'}
                placeholder="Введите пароль" />
            {error && <Feedback>{error}</Feedback>}
            <Button variant="primary" type="submit">
              {busy ? 'Подождите…' : register ? 'Создать аккаунт' : 'Войти'}
              <span aria-hidden="true">↗</span>
            </Button>
          </fieldset>
        </form>
        <p className="auth-note">{register
          ? 'После регистрации вам нужно будет войти в аккаунт.'
          : 'Здесь начинается ваш маршрут.'}</p>
      </div>
      <span className="auth-bottom">AnimeMap © {new Date().getFullYear()}</span>
    </section>
  </main>;
}
