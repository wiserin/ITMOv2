import type { AccountResponse } from '../../api/client';

export function Avatar({ account }: { account: AccountResponse }) {
  return <span className="avatar" aria-hidden="true">
    {(account.display_name || account.username).slice(0, 1)
      .toUpperCase()}
  </span>;
}

