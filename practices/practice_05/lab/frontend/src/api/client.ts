export interface AccountResponse {
  id: string;
  email: string;
  username: string;
  display_name: string | null;
  role: 'user' | 'moderator' | 'admin';
  is_active: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest extends LoginRequest {
  username: string;
  display_name?: string | null;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/v1${path}`, {
      ...options,
      credentials: 'same-origin',
      cache: 'no-store',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw error;
    }
    throw new ApiError(0, 'Нет соединения. Попробуйте ещё раз.');
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const messages: Record<number, string> = {
      400: 'Проверьте введённые данные.',
      401: 'Сессия истекла. Войдите снова.',
      403: 'Недостаточно прав для поиска пользователей.',
      409: 'Этот email уже зарегистрирован.',
      502: 'API недоступен. Попробуйте немного позже.',
      503: 'Сервис временно недоступен.',
      504: 'Сервер не ответил вовремя. Попробуйте ещё раз.',
    };
    throw new ApiError(
      response.status,
      messages[response.status] || data.message ||
        'Не удалось выполнить запрос.',
    );
  }
  return data as T;
}

export const api = {
  me: () => request<AccountResponse>('/account/me'),
  login: (data: LoginRequest) => request('/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  register: (data: RegisterRequest) => request('/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  find: (prefix: string, offset: number, signal: AbortSignal) =>
    request<{ accounts: AccountResponse[] }>(
      `/account/find/${encodeURIComponent(prefix)}` +
        `?limit=20&offset=${offset}`,
      { signal },
    ),
};

export function canModerate(account: AccountResponse) {
  return ['admin', 'moderator'].includes(account.role);
}
