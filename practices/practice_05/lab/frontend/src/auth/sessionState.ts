import type { AccountResponse } from '../api/client';

export type FailureReason = 'network' | 'timeout' | 'unavailable' | 'other';
export type AuthOperation = { operationId: number; kind: 'login' | 'logout' };
export type LogoutAttempt = {
  attemptId: number; operationId: number; capturedGeneration: number;
  startedAt: number; deadline: number; terminal: boolean;
};
export type ProtectedRequestContext = { generation: number; requestId: number };
export type AuthState = {
  account: AccountResponse | null;
  generation: number;
  sequence: number;
  operation: AuthOperation | null;
  attempt: LogoutAttempt | null;
  logout: 'idle' | 'pending' | 'failed';
  reason: FailureReason | null;
  notice: 'signed-out' | 'session-invalid' | null;
};

export function initialState(): AuthState {
  return { account: null, generation: 0, sequence: 0, operation: null,
    attempt: null, logout: 'idle', reason: null, notice: null };
}

export function acquire(state: AuthState, kind: AuthOperation['kind'], now: number): AuthState | null {
  if (state.operation) return null;
  const id = state.sequence + 1;
  return { ...state, sequence: id, operation: { operationId: id, kind },
    ...(kind === 'logout' ? {
      attempt: { attemptId: id, operationId: id,
        capturedGeneration: state.generation, startedAt: now,
        deadline: now + 20000, terminal: false },
      logout: 'pending' as const, reason: null,
    } : {}) };
}

export function clearAuth(state: AuthState): AuthState {
  return { ...state, generation: state.generation + 1, account: null,
    logout: 'idle', reason: null, notice: null };
}

export function replaceAccount(state: AuthState, account: AccountResponse): AuthState {
  return { ...clearAuth(state), account };
}

export function release(state: AuthState, operationId: number): AuthState {
  return state.operation?.operationId === operationId
    ? { ...state, operation: null } : state;
}

export function isCurrent(state: AuthState, attempt: LogoutAttempt): boolean {
  return state.generation === attempt.capturedGeneration &&
    state.attempt?.attemptId === attempt.attemptId &&
    !state.attempt.terminal && !attempt.terminal;
}

export function finishLogout(state: AuthState, attempt: LogoutAttempt,
  outcome: 'closed' | 'invalid' | 'failure', reason: FailureReason = 'other'): AuthState {
  if (state.attempt?.attemptId !== attempt.attemptId || state.attempt.terminal) return state;
  const current = isCurrent(state, attempt);
  let next: AuthState = { ...state, attempt: { ...state.attempt, terminal: true } };
  if (current && outcome !== 'failure') {
    next = { ...clearAuth(next), notice: outcome === 'closed'
      ? 'signed-out' : 'session-invalid' };
  } else if (current && next.account) {
    next = { ...next, logout: 'failed', reason };
  }
  return release(next, attempt.operationId);
}
