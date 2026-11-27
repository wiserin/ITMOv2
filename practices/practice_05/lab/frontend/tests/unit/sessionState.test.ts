import { describe, expect, it } from 'vitest';
import {
  initialState, acquire, clearAuth, replaceAccount, release,
  finishLogout, isCurrent,
} from '../../src/auth/sessionState';

describe('auth generation and operation ownership', () => {
  it('keeps one slot through clear, rejecting login and autoqueue', () => {
    const start = acquire(initialState(), 'logout', 100)!;
    expect(start.attempt?.deadline).toBe(20100);
    expect(acquire(start, 'login', 101)).toBeNull();
    const cleared = clearAuth(start);
    expect(cleared.generation).toBe(start.generation + 1);
    expect(cleared.operation).toEqual(start.operation);
    expect(acquire(cleared, 'login', 200)).toBeNull();
    expect(isCurrent(cleared, start.attempt!)).toBe(false);
  });

  it('does not release a different owner', () => {
    const login = acquire(initialState(), 'login', 0)!;
    expect(release(login, login.operation!.operationId + 1)).toBe(login);
    expect(release(login, login.operation!.operationId).operation).toBeNull();
  });

  it('terminalizes before release and never revives an old attempt', () => {
    const start = acquire(initialState(), 'logout', 0)!;
    const old = start.attempt!;
    const done = finishLogout(start, old, 'failure', 'timeout');
    expect(done.attempt?.terminal).toBe(true);
    expect(done.operation).toBeNull();
    const next = acquire(done, 'logout', 20001)!;
    expect(next.attempt?.attemptId).not.toBe(old.attemptId);
    expect(finishLogout(next, old, 'closed')).toBe(next);
    expect(release(next, old.operationId)).toBe(next);
  });

  it('clear permits own completion without changing notices or generation', () => {
    const start = acquire(initialState(), 'logout', 0)!;
    const cleared = clearAuth(start);
    const completed = finishLogout(cleared, start.attempt!, 'closed');
    expect(completed.generation).toBe(cleared.generation);
    expect(completed.notice).toBeNull();
    expect(completed.operation).toBeNull();
    expect(completed.account).toBeNull();
  });

  it('replacement changes generation and clears old notices', () => {
    const start = acquire(initialState(), 'logout', 0)!;
    const done = finishLogout(start, start.attempt!, 'closed');
    expect(done.notice).toBe('signed-out');
    const next = replaceAccount(done, { id: 'new' } as never);
    expect(next.generation).toBe(done.generation + 1);
    expect(next.notice).toBeNull();
  });
});
