import {
    useId, useLayoutEffect, useRef, type MouseEvent, type ReactNode,
} from 'react';
import { Button } from './Button';

export type DialogProps = {
    open: boolean;
    title: string;
    onClose: () => void;
    children: ReactNode;
    closeLabel?: string;
    closeOnBackdrop?: boolean;
    className?: string;
};

export function Dialog({
    open, title, onClose, children, closeLabel = 'Закрыть диалог',
    closeOnBackdrop = true, className = '',
}: DialogProps) {
    const ref = useRef<HTMLDialogElement>(null);
    const titleId = useId();
    const backdropPressed = useRef(false);
    useLayoutEffect(() => {
        if (!open) return;
        const dialog = ref.current;
        const previous = document.activeElement;
        dialog?.showModal();
        return () => {
            dialog?.close();
            if (previous instanceof HTMLElement
                && previous.isConnected) {
                previous.focus();
            }
        };
    }, [open]);

    function outside(event: MouseEvent<HTMLDialogElement>) {
        const rect = event.currentTarget.getBoundingClientRect();
        return event.target === event.currentTarget
            && (event.clientX < rect.left
                || event.clientX > rect.right
                || event.clientY < rect.top
                || event.clientY > rect.bottom);
    }

    return <dialog ref={ref} aria-labelledby={titleId}
        className={`ui-dialog ${className}`}
        onCancel={event => { event.preventDefault(); onClose(); }}
        onKeyDown={event => {
            if (event.key !== 'Tab') return;
            const elements = Array.from(
                event.currentTarget.querySelectorAll<HTMLElement>(
                    'a[href], button, input, select, textarea, '
                        + '[tabindex]'
                )
            ).filter(element => element.tabIndex >= 0
                && !element.matches(':disabled')
                && !element.closest('[inert]')
                && element.getClientRects().length > 0);
            const first = elements[0];
            const last = elements[elements.length - 1];
            const active = document.activeElement;
            if (event.shiftKey && active === first) {
                event.preventDefault();
                last?.focus();
            } else if (!event.shiftKey && active === last) {
                event.preventDefault();
                first?.focus();
            }
        }}
        onPointerDown={event => {
            backdropPressed.current = outside(event);
        }}
        onClick={event => {
            if (closeOnBackdrop && backdropPressed.current
                && outside(event)) onClose();
            backdropPressed.current = false;
        }}>
        <div className="ui-dialog__body">
            <div className="ui-dialog__heading">
                <h2 id={titleId}>{title}</h2>
                <Button variant="icon" onClick={onClose}
                    aria-label={closeLabel}>×</Button>
            </div>
            {children}
        </div>
    </dialog>;
}
