import { useEffect, useRef } from 'react';
import type { AccountResponse } from '../api/client';
import { AccountDetails } from './AccountDetails';

export function AccountModal({ account, onClose }: {
  account: AccountResponse;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    dialog.current?.showModal();
    return () => {
      previous?.focus();
    };
  }, []);
  return <dialog ref={dialog} className="account-modal"
    aria-labelledby="modal-title" onCancel={onClose}
    onClick={event => {
      if (event.target === event.currentTarget) onClose();
    }}>
    <div className="modal-body">
      <div className="section-top">
        <p className="eyebrow" id="modal-title">Профиль пользователя</p>
        <button className="icon-button" onClick={onClose}
          aria-label="Закрыть карточку">×</button>
      </div>
      <AccountDetails account={account} />
    </div>
  </dialog>;
}
