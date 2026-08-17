const STORAGE_KEY = "talent-mirror-app-password";

export function getStoredPassword(): string {
  return sessionStorage.getItem(STORAGE_KEY) || "";
}

export function setStoredPassword(password: string): void {
  sessionStorage.setItem(STORAGE_KEY, password);
}

export function clearStoredPassword(): void {
  sessionStorage.removeItem(STORAGE_KEY);
}

/** Verifica a senha de acesso contra o backend, sem guardar nada em caso de erro. */
export async function checkPassword(base: string, password: string): Promise<boolean> {
  const response = await fetch(`${base}/resumes/stats/by-category`, {
    headers: { "X-App-Password": password },
  });
  return response.ok;
}
