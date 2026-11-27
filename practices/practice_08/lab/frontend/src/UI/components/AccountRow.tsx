import type { AccountResponse } from '../../api/client';
import { Avatar } from './Avatar';
import { roleNames } from './roleNames';
import { Button } from './Button';

export function AccountRow({ account, onSelect }: {
  account: AccountResponse;
  onSelect: () => void;
}) {
  return <Button variant="plain" className="user-row"
    onClick={onSelect}>
    <Avatar account={account} />
    <span className="user-info">
      <strong>{account.display_name || account.username}</strong>
      <span>@{account.username} · {account.email}</span>
    </span>
    <span className={`role-badge ${account.role}`}>
      {roleNames[account.role]}</span>
    <span className="row-arrow" aria-hidden="true">↗</span>
  </Button>;
}
