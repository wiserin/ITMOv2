import { useState, type FormEvent } from 'react';
import { api, ApiError, type AccountResponse } from '../api/client';
import { Brand } from '../components/Brand';

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
    <section className="auth-story">
      <Brand />
      <div className="story-copy">
        <span className="eyebrow">Твоя следующая история</span>
        <h1>Любимые миры.<br />Реальные места<span>.</span></h1>
        <p>У каждого кадра есть координаты.<br />
          Скоро найдём их вместе.</p>
      </div>
      <div className="map-art" aria-hidden="true">
        <div className="map-ring ring-one" />
        <div className="map-ring ring-two" />
        <div className="map-route" />
        <span className="map-pin pin-one">✦</span>
        <span className="map-pin pin-two">✦</span>
        <span className="map-label">35°40′ N &nbsp; 139°42′ E</span>
        <span className="map-city">TOKYO, JP ↗</span>
      </div>
      <span className="story-footer">ANIME MEETS THE WORLD</span>
    </section>
    <section className="auth-form-side">
      <div className="auth-box">
        <div className="auth-tabs" aria-label="Авторизация">
          <a href="#/login" aria-current={!register ? 'page' : undefined}
            onClick={() => setError('')}>Вход</a>
          <a href="#/register"
            aria-current={register ? 'page' : undefined}
            onClick={() => { setError(''); setSuccess(false); }}>
            Регистрация
          </a>
        </div>
        <p className="eyebrow">Добро пожаловать в AnimeMap</p>
        <h2>{register ? 'Начнём путешествие' : 'С возвращением'}</h2>
        <p className="muted auth-intro">{register
          ? 'Создайте аккаунт для своих будущих открытий.'
          : 'Войдите, чтобы быть ближе к любимым историям.'}</p>
        {success && !register && <p className="success" role="status">
          Аккаунт создан. Войдите с вашим email и паролем.
        </p>}
        <form onSubmit={submit} key={String(register)}>
          <fieldset disabled={busy}>
            {register && <>
              <label>Имя пользователя
                <input name="username" required maxLength={100}
                  autoComplete="username" placeholder="anime-fan" />
              </label>
              <label>Отображаемое имя <span>необязательно</span>
                <input name="display_name" maxLength={100}
                  autoComplete="nickname" placeholder="Как вас называть?" />
              </label>
            </>}
            <label>Email
              <input name="email" type="email" required
                maxLength={254} autoComplete="email"
                value={email} onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com" />
            </label>
            <label>Пароль
              <input name="password" type="password" required
                autoComplete={register ? 'new-password' : 'current-password'}
                placeholder="Введите пароль" />
            </label>
            {error && <p className="error" role="alert">{error}</p>}
            <button className="primary" type="submit">
              {busy ? 'Подождите…' : register ? 'Создать аккаунт' : 'Войти'}
              <span aria-hidden="true">↗</span>
            </button>
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
