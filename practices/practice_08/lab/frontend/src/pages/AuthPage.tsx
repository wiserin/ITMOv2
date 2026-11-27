import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError, type AccountResponse } from '../api/client';
import { AuthStory } from '../components/AuthStory';
import { AuthTabs } from '../components/AuthTabs';
import { Button, Feedback, TextField } from '../UI';

export function AuthPage({ register, onLogin }: {
    register: boolean;
    onLogin: (account: AccountResponse) => void;
}) {
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);
    const [email, setEmail] = useState('');
    const submitting = useRef(false);
    const heading = useRef<HTMLHeadingElement>(null);
    const submitLabel = busy ? 'Подождите…'
        : register ? 'Создать аккаунт' : 'Войти';
    useEffect(() => { heading.current?.focus(); }, [register]);

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (submitting.current) return;
        submitting.current = true;
        setBusy(true);
        setError('');
        try {
            const form = new FormData(event.currentTarget);
            const password = String(form.get('password') || '');
            const normalizedEmail = email.trim().toLowerCase();
            if (register) {
                const username = String(form.get('username') || '')
                    .trim();
                if (!username) {
                    throw new Error('Введите имя пользователя.');
                }
                const displayName = String(
                    form.get('display_name') || ''
                ).trim() || null;
                await api.register({
                    email: normalizedEmail, password, username,
                    display_name: displayName,
                });
                setSuccess(true);
                window.location.hash = '/login';
            } else {
                await api.login({ email: normalizedEmail, password });
                onLogin(await api.me());
                window.location.hash = '/';
            }
        } catch (reason) {
            const invalid = reason instanceof ApiError
                && reason.status === 401;
            setError(invalid
                ? 'Неверный email или пароль, либо аккаунт неактивен.'
                : reason instanceof Error
                    ? reason.message : 'Ошибка запроса.');
        } finally {
            submitting.current = false;
            setBusy(false);
        }
    }

    return <main className="am-auth-layout">
        <AuthStory />
        <section className="am-auth-form-side">
            <div className="am-auth-box">
                <AuthTabs register={register}
                    onLogin={() => setError('')}
                    onRegister={() => {
                        setError('');
                        setSuccess(false);
                    }} />
                <p className="am-eyebrow">
                    Добро пожаловать в AnimeMap
                </p>
                <h2 ref={heading} tabIndex={-1}>
                    {register
                        ? 'Начнём путешествие' : 'С возвращением'}
                </h2>
                <p className="am-muted am-auth-intro">{register
                    ? 'Создайте аккаунт для своих будущих открытий.'
                    : 'Войдите, чтобы быть ближе к любимым историям.'}
                </p>
                {success && !register && <Feedback variant="success">
                    Аккаунт создан. Войдите с вашим email и паролем.
                </Feedback>}
                <form onSubmit={submit} key={String(register)}>
                    <fieldset disabled={busy} aria-busy={busy}>
                        {register && <>
                            <TextField label="Имя пользователя"
                                name="username" required
                                maxLength={100} autoComplete="username"
                                placeholder="anime-fan" />
                            <TextField label="Отображаемое имя"
                                hint="необязательно"
                                name="display_name" maxLength={100}
                                autoComplete="nickname"
                                placeholder="Как вас называть?" />
                        </>}
                        <TextField label="Email" name="email"
                            type="email" required maxLength={254}
                            autoComplete="email" value={email}
                            onChange={e => setEmail(e.target.value)}
                            placeholder="you@example.com" />
                        <TextField label="Пароль" name="password"
                            type="password" required
                            autoComplete={register
                                ? 'new-password' : 'current-password'}
                            placeholder="Введите пароль" />
                        {error && <Feedback>{error}</Feedback>}
                        <Button variant="primary" type="submit"
                            loading={busy}>
                            {submitLabel}
                            <span aria-hidden="true">↗</span>
                        </Button>
                    </fieldset>
                </form>
                <p className="am-auth-note">{register
                    ? 'После регистрации вам нужно будет '
                        + 'войти в аккаунт.'
                    : 'Здесь начинается ваш маршрут.'}</p>
            </div>
            <span className="am-auth-bottom">
                AnimeMap © {new Date().getFullYear()}
            </span>
        </section>
    </main>;
}
