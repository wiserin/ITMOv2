import { act, renderHook } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { useAuthSession } from '../../src/auth/useAuthSession';
import { logout } from '../../src/api/logout';
import { deferred } from './setup';

vi.mock('../../src/api/logout', () => ({ logout: vi.fn() }));

export const account = { id: 'a', email: 'a@example.com', username: 'a',
  display_name: null, role: 'admin' as const, is_active: true };

it('acquires synchronously before render and clears only on confirmed result', async () => {
  const waiting = deferred<{ kind: 'closed' }>();
  vi.mocked(logout).mockReturnValue(waiting.promise);
  const { result } = renderHook(() => useAuthSession());
  act(() => result.current.installAccount(account));
  const generation = result.current.state.generation;
  act(() => { void result.current.startLogout(); void result.current.startLogout(); });
  expect(logout).toHaveBeenCalledTimes(1);
  expect(result.current.state.account).toEqual(account);
  expect(result.current.state.logout).toBe('pending');
  await act(async () => waiting.resolve({ kind: 'closed' }));
  expect(result.current.state.account).toBeNull();
  expect(result.current.state.generation).toBeGreaterThan(generation);
  expect(result.current.state.operation).toBeNull();
  expect(result.current.state.notice).toBe('signed-out');
  expect(window.location.hash).toBe('#/login');
});
