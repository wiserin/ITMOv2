import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { App } from '../../src/App';
import { api } from '../../src/api/client';
import { logout } from '../../src/api/logout';
import { deferred } from './setup';

vi.mock('../../src/api/logout', () => ({ logout: vi.fn() }));
const account = { id: 'a', email: 'a@example.com', username: 'Current user',
  display_name: null, role: 'admin' as const, is_active: true };

it.each(['/', '/account', '/admin'])('closes menu, clears %s and opens login', async path => {
  window.location.hash = path;
  const me = vi.spyOn(api, 'me').mockResolvedValue(account);
  const waiting = deferred<{ kind: 'closed' }>();
  vi.mocked(logout).mockReturnValue(waiting.promise);
  render(<App />);
  const trigger = await screen.findByRole('button', { name: 'Меню аккаунта' });
  const callsBeforeLogout = me.mock.calls.length;
  fireEvent.click(trigger);
  fireEvent.click(screen.getByRole('button', { name: /Выйти/ }));
  expect(screen.queryByRole('navigation', { name: 'Аккаунт' })).toBeNull();
  expect(screen.getByText('Выходим…').getAttribute('role')).toBe('status');
  expect(document.activeElement).toBe(trigger);
  await act(async () => waiting.resolve({ kind: 'closed' }));
  await screen.findByText('Вы вышли из аккаунта.');
  expect(screen.queryByRole('button', { name: 'Меню аккаунта' })).toBeNull();
  expect(screen.queryByText(account.email)).toBeNull();
  expect(me).toHaveBeenCalledTimes(callsBeforeLogout);
  await waitFor(() => expect(document.activeElement).toBe(
    screen.getByRole('heading', { name: 'С возвращением' })));
});
