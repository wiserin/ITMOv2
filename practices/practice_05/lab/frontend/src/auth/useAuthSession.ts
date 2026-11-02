import { useCallback, useRef, useState } from 'react';
import { api, type AccountResponse, type LoginRequest } from '../api/client';
import { logout } from '../api/logout';
import {
  initialState, acquire, clearAuth, replaceAccount, release, finishLogout,
  type AuthState,
} from './sessionState';

export function useAuthSession() {
  const ref = useRef(initialState());
  const [state, setState] = useState(ref.current);
  const update = useCallback((next: AuthState) => {
    ref.current = next;
    setState(next);
  }, []);
  const currentGeneration = useCallback(() => ref.current.generation, []);
  const allowed = useCallback((generation: number) =>
    generation === ref.current.generation && ref.current.logout !== 'pending', []);
  const installAccount = useCallback((account: AccountResponse, generation?: number) => {
    if (generation !== undefined && generation !== ref.current.generation) return;
    update(replaceAccount(ref.current, account));
  }, [update]);
  const onExpired = useCallback((generation: number) => {
    if (generation !== ref.current.generation) return;
    update({ ...clearAuth(ref.current), notice: 'session-invalid' });
    window.location.hash = '/login';
  }, [update]);
  const startLogout = useCallback(async () => {
    if (!ref.current.account) return;
    const next = acquire(ref.current, 'logout', Date.now());
    if (!next) return;
    const attempt = next.attempt!;
    update(next);
    let outcome;
    try { outcome = await logout({ deadline: attempt.deadline }); }
    catch { outcome = { kind: 'failure' as const, reason: 'network' as const }; }
    const before = ref.current;
    const after = finishLogout(before, attempt, outcome.kind,
      outcome.kind === 'failure' ? outcome.reason : undefined);
    update(after);
    if (after.generation !== before.generation) window.location.hash = '/login';
  }, [update]);
  const login = useCallback(async (data: LoginRequest) => {
    const next = acquire(ref.current, 'login', Date.now());
    if (!next) return;
    const owner = next.operation!.operationId;
    const generation = next.generation;
    update({ ...next, notice: null });
    try {
      await api.login(data);
      const account = await api.me();
      if (ref.current.operation?.operationId === owner &&
          ref.current.generation === generation) {
        update(replaceAccount(ref.current, account));
        window.location.hash = '/';
      }
    } finally {
      update(release(ref.current, owner));
    }
  }, [update]);
  const dismiss = useCallback(() => {
    if (ref.current.logout === 'pending') return;
    update({ ...ref.current, logout: 'idle', reason: null, notice: null });
  }, [update]);
  return { state, currentGeneration, allowed, installAccount,
    startLogout, login, onExpired, dismiss };
}
