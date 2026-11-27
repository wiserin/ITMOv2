import type { FailureReason } from '../auth/sessionState';

export type LogoutResult = { kind: 'closed' } | { kind: 'invalid' } |
  { kind: 'failure'; reason: FailureReason };

export async function logout({ deadline = Date.now() + 20000 } = {}): Promise<LogoutResult> {
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout>;
  let status: number | undefined;
  const timeout = new Promise<LogoutResult>(resolve => {
    timer = setTimeout(() => {
      resolve({ kind: 'failure', reason: 'timeout' });
      controller.abort();
    }, Math.max(0, deadline - Date.now()));
  });
  const request = async (): Promise<LogoutResult> => {
    try {
      const response = await fetch('/v1/auth/logout', {
        method: 'POST', credentials: 'same-origin', cache: 'no-store',
        headers: { 'X-AnimeMap-Logout': '1' }, signal: controller.signal,
        redirect: 'manual',
      });
      status = response.status;
      // Read completion belongs to the same budget; parsing is unnecessary.
      await response.arrayBuffer().catch(() => undefined);
      if (status === 204) return { kind: 'closed' };
      if (status === 401) return { kind: 'invalid' };
      return { kind: 'failure', reason: status === 504 ? 'timeout'
        : status === 502 || status === 503 ? 'unavailable'
        : status === 0 ? 'network' : 'other' };
    } catch {
      return { kind: 'failure', reason: status === undefined || status === 0
        ? 'network' : 'other' };
    }
  };
  try { return await Promise.race([request(), timeout]); }
  finally { clearTimeout(timer!); }
}

export const logoutMessages = {
  network: 'Не удалось подтвердить выход: нет соединения. Попробуйте ещё раз.',
  timeout: 'Не удалось подтвердить выход: сервер не ответил вовремя. Попробуйте ещё раз.',
  unavailable: 'Не удалось подтвердить выход: сервис временно недоступен. Попробуйте позже.',
  other: 'Не удалось подтвердить выход. Попробуйте ещё раз.',
};
