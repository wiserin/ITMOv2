export function AuthTabs({ register, onLogin, onRegister }: {
  register: boolean;
  onLogin: () => void;
  onRegister: () => void;
}) {
  return <nav className="auth-tabs" aria-label="Авторизация">
    <a href="#/login" aria-current={!register ? 'page' : undefined}
      onClick={onLogin}>Вход</a>
    <a href="#/register"
      aria-current={register ? 'page' : undefined}
      onClick={onRegister}>Регистрация</a>
  </nav>;
}
