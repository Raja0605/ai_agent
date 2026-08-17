/**
 * Single source of truth for the backend base URL.
 *
 * Build-time value (Vite inlines it), so it must be something the *browser*
 * can resolve — not a docker-internal hostname like `backend:8000`.
 *
 * The default is the relative path `/api`, served by the nginx reverse proxy
 * in the production image. A previous absolute default of
 * `http://localhost:8000/api` was baked into the bundle, which meant the
 * dashboard only worked when opened on the Docker host itself: from any other
 * device "localhost" pointed at that device and every request failed. A
 * relative path always resolves back to whoever served the page.
 *
 * For `npm run dev`, vite.config.ts proxies /api to localhost:8000, so the
 * same relative path works there too.
 */
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || '/api';

/** Wait helper for retry backoff. */
const wait = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * fetch() that retries while the backend is still coming up.
 *
 * The page is served by nginx the moment the container starts, but the API
 * needs to run migrations first. Requests fired on mount during that window
 * fail at the TCP level — which surfaces in the browser as a bare "Failed to
 * fetch" with no status code, and looks to the user like the app is broken.
 *
 * Only connection-level failures and 502/503/504 are retried; a real 4xx is
 * an answer and is returned immediately.
 */
export async function fetchWithRetry(
  input: string,
  init?: RequestInit,
  attempts = 4
): Promise<Response> {
  let lastError: unknown;

  for (let attempt = 0; attempt < attempts; attempt++) {
    if (attempt > 0) {
      // 400ms, 800ms, 1600ms — covers a normal migrate-and-boot cycle.
      await wait(400 * 2 ** (attempt - 1));
    }

    try {
      const response = await fetch(input, init);
      if (response.status === 502 || response.status === 503 || response.status === 504) {
        lastError = new Error(`Backend not ready (${response.status})`);
        continue;
      }
      return response;
    } catch (err) {
      // TypeError here is fetch's network-level failure.
      lastError = err;
    }
  }

  throw new Error(
    'Could not reach the API. If you just started the stack, the backend may ' +
      'still be running database migrations — wait a few seconds and retry. ' +
      `(${lastError instanceof Error ? lastError.message : String(lastError)})`
  );
}
