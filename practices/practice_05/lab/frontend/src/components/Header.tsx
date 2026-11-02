import { useEffect, useRef, useState } from 'react';
import { canModerate, type AccountResponse } from '../api/client';
import { Avatar, roleNames } from './AccountDetails';
import { Brand } from './Brand';

export function Header({ account, busy, onLogout }: {
  account: AccountResponse; busy: boolean; onLogout: () => void;
}) {
  const [open, setOpen] = useState(false);
  const menu = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    function outside(event: PointerEvent) {
      if (!menu.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('pointerdown', outside);
    return () => document.removeEventListener('pointerdown', outside);
  }, []);

  return <header className="header">
    <a href="#/" aria-label="AnimeMap — главная"><Brand /></a>
    <span className="header-caption">Из аниме — в реальность</span>
    <div className="user-menu" ref={menu}
      onPointerEnter={event => {
        if (!busy && event.pointerType === 'mouse') setOpen(true);
      }}
      onPointerLeave={event => {
        if (event.pointerType === 'mouse') setOpen(false);
      }}
      onBlur={event => {
        if (!event.currentTarget.contains(event.relatedTarget)) {
          setOpen(false);
        }
      }}
      onKeyDown={event => {
        if (event.key === 'Escape') {
          setOpen(false);
          trigger.current?.focus();
        }
      }}>
      <button className="avatar-button" ref={trigger}
        aria-label="Меню аккаунта" aria-expanded={open}
        aria-controls="account-menu"
        aria-disabled={busy} aria-busy={busy}
        onClick={() => { if (!busy) setOpen(value => !value); }}>
        <Avatar account={account} />
      </button>
      {open && !busy && <div className="dropdown-wrap">
        <nav className="dropdown" id="account-menu"
          aria-label="Аккаунт">
          <div className="menu-identity">
            <strong>{account.display_name || account.username}</strong>
            <small>{roleNames[account.role]}</small>
          </div>
          <a href="#/account" onClick={() => setOpen(false)}>
            <span aria-hidden="true">◎</span> Аккаунт
          </a>
          {canModerate(account) &&
            <a href="#/admin" onClick={() => setOpen(false)}>
              <span aria-hidden="true">⊞</span> Admin Panel
            </a>}
          <button onClick={() => {
            setOpen(false);
            trigger.current?.focus();
            if (!busy) onLogout();
          }}><span aria-hidden="true">↗</span> Выйти
          </button>
        </nav>
      </div>}
    </div>
  </header>;
}
