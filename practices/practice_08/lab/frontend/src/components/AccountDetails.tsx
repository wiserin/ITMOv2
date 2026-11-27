import type { AccountResponse } from '../api/client';

import { Avatar } from '../UI';
import { roleNames } from './roleNames';

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
        <div className="am-profile-heading">
            <Avatar size="lg" name={account.display_name || account.username}
                aria-hidden="true" />
            <div>
                <h2>{account.display_name || account.username}</h2>
                <span className="am-muted">@{account.username}</span>
            </div>
        </div>
        <dl className="am-details">
            {fields.map(([label, value]) => <div key={label}>
                <dt>{label}</dt><dd>{value}</dd>
            </div>)}
        </dl>
    </>;
}
