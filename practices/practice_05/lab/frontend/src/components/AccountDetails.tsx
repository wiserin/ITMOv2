import type { AccountResponse } from '../api/client';

export const roleNames = {
  user: 'Пользователь',
  moderator: 'Модератор',
  admin: 'Администратор',
};

export function Avatar({ account }: { account: AccountResponse }) {
  return <span className="avatar" aria-hidden="true">
    {(account.display_name || account.username).slice(0, 1)
      .toUpperCase()}
  </span>;
}

export function AccountDetails(
  { account }: { account: AccountResponse },
) {
  const fields = [
    ['Имя пользователя', account.username],
    ['Email', account.email],
    ['Отображаемое имя', account.display_name || 'Не указано'],
    ['Роль', roleNames[account.role]],
    ['Статус', account.is_active ? 'Активен' : 'Неактивен'],
    ['ID аккаунта', account.id],
  ];
  return <>
    <div className="profile-heading">
      <Avatar account={account} />
      <div>
        <h2>{account.display_name || account.username}</h2>
        <span className="muted">@{account.username}</span>
      </div>
    </div>
    <dl className="details">
      {fields.map(([label, value]) => <div key={label}>
        <dt>{label}</dt><dd>{value}</dd>
      </div>)}
    </dl>
  </>;
}
