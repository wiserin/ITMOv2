import { useEffect, useRef, useState } from 'react';
import { canModerate, type AccountResponse } from '../api/client';
import { Avatar, roleNames } from './AccountDetails';
import { Brand } from './Brand';

export function Header({ account }: { account: AccountResponse }) {
  const [open, setOpen] = useState(false);
  const [notice, setNotice] = useState(false);
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
        if (event.pointerType === 'mouse') setOpen(true);
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
        onClick={() => setOpen(value => !value)}>
        <Avatar account={account} />
      </button>
      {open && <div className="dropdown-wrap">
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
            setNotice(true);
            setOpen(false);
          }}><span aria-hidden="true">↗</span> Выйти
            <small>Скоро</small>
          </button>
        </nav>
      </div>}
    </div>
    {notice && <div className="toast" role="status">
      Выход появится позже. Ваша сессия остаётся активной.
      <button aria-label="Закрыть уведомление"
        onClick={() => setNotice(false)}>×</button>
    </div>}
  </header>;
}
