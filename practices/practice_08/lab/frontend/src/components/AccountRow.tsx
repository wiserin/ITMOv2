import type { AccountResponse } from '../api/client';
import { Avatar } from '../UI';
import { roleNames } from './roleNames';
import { Button } from '../UI';

export function AccountRow({ account, onSelect }: {
    account: AccountResponse;
    onSelect: () => void;
}) {
    return <Button variant="plain" className="am-user-row"
        onClick={onSelect}>
        <Avatar name={account.display_name || account.username}
                aria-hidden="true" />
        <span className="am-user-info">
            <strong>{account.display_name || account.username}</strong>
            <span>@{account.username} · {account.email}</span>
        </span>
        <span className={`am-role-badge am-${account.role}`}>
            {roleNames[account.role]}</span>
        <span className="am-row-arrow" aria-hidden="true">↗</span>
    </Button>;
}
