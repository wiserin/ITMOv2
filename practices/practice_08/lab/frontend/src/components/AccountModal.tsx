import type { AccountResponse } from '../api/client';
import { Dialog } from '../UI';
import { AccountDetails } from './AccountDetails';

export function AccountModal({ account, onClose }: {
        account: AccountResponse;
        onClose: () => void;
}) {
        return <Dialog open title="Профиль пользователя"
                closeLabel="Закрыть карточку" onClose={onClose}>
                <AccountDetails account={account} />
        </Dialog>;
}
