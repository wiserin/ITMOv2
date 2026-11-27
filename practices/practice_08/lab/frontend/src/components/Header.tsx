import { useEffect, useId, useRef, useState } from 'react';
import { canModerate, type AccountResponse } from '../api/client';
import { Avatar } from '../UI';
import { roleNames } from './roleNames';
import { Button } from '../UI';
import { Brand } from './Brand';

export function Header({ account }: { account: AccountResponse }) {
    const [mode, setMode] = useState<'closed' | 'hover' | 'pinned'>('closed');
    const open = mode !== 'closed';
    const menuId = useId();
    const [notice, setNotice] = useState(false);
    const menu = useRef<HTMLDivElement>(null);
    const trigger = useRef<HTMLButtonElement>(null);

    useEffect(() => {
        function outside(event: PointerEvent) {
            if (!menu.current?.contains(event.target as Node)) {
                if (menu.current?.contains(document.activeElement)) {
                    const target = event.target as Element;
                    const focusable = target.closest(
                        'a, button, input, select, textarea, [tabindex]'
                    );
                    if (!focusable) event.preventDefault();
                    trigger.current?.focus();
                }
                setMode('closed');
            }
        }
        document.addEventListener('pointerdown', outside);
        return () => document.removeEventListener('pointerdown', outside);
    }, []);

    return <header className="am-header">
        <a href="#/" aria-label="AnimeMap — главная"><Brand /></a>
        <span className="am-header-caption">Из аниме — в реальность</span>
        <div className="am-user-menu" ref={menu}
            onPointerEnter={event => {
                if (event.pointerType === 'mouse') {
                    setMode(value => value === 'closed' ? 'hover' : value);
                }
            }}
            onPointerLeave={event => {
                if (event.pointerType === 'mouse'
                        && !menu.current?.contains(document.activeElement)) {
                    setMode(value => value === 'hover' ? 'closed' : value);
                }
            }}
            onBlur={event => {
                if (!event.currentTarget.contains(event.relatedTarget)) {
                    setMode('closed');
                }
            }}
            onKeyDown={event => {
                if (event.key === 'Escape') {
                    setMode('closed');
                    trigger.current?.focus();
                }
            }}>
            <Button variant="plain" className="am-avatar-button" ref={trigger}
                aria-label="Меню аккаунта" aria-expanded={open}
                aria-controls={open ? menuId : undefined}
                onClick={() => setMode(value =>
                    value === 'pinned' ? 'closed' : 'pinned')}>
                <Avatar name={account.display_name || account.username}
                aria-hidden="true" />
            </Button>
            {open && <div className="am-dropdown-wrap">
                <nav className="am-dropdown" id={menuId}
                    aria-label="Аккаунт">
                    <div className="am-menu-identity">
                        <strong>
                            {account.display_name || account.username}
                        </strong>
                        <small>{roleNames[account.role]}</small>
                    </div>
                    <a href="#/account" onClick={() => setMode('closed')}>
                        <span aria-hidden="true">◎</span> Аккаунт
                    </a>
                    {canModerate(account) &&
                        <a href="#/admin" onClick={() => setMode('closed')}>
                            <span aria-hidden="true">⊞</span> Admin Panel
                        </a>}
                    <Button variant="plain" onClick={() => {
                        trigger.current?.focus();
                        setNotice(true);
                        setMode('closed');
                    }}><span aria-hidden="true">↗</span> Выйти
                        <small>Скоро</small>
                    </Button>
                </nav>
            </div>}
        </div>
        {notice && <div className="am-toast" role="status">
            Выход появится позже. Ваша сессия остаётся активной.
            <Button variant="plain" aria-label="Закрыть уведомление"
                onClick={() => setNotice(false)}>×</Button>
        </div>}
    </header>;
}
