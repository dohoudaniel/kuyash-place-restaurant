import { API_ORIGIN, ensureCsrfCookie, readCsrfToken } from "@/lib/api/client";

export type SocialProvider = "google" | "facebook";

interface HeadlessConfig {
  data?: { socialaccount?: { providers?: { id: string; name: string; flows?: string[] }[] } };
}

/**
 * Which social providers the backend has credentials for.
 *
 * Buttons for an unconfigured provider would send the customer to an error
 * page, so the list comes from allauth's own config endpoint rather than being
 * hardcoded. An unreachable API yields no providers, which hides the buttons.
 */
export async function fetchSocialProviders(): Promise<SocialProvider[]> {
  try {
    const response = await fetch(`${API_ORIGIN}/_allauth/browser/v1/config`, { credentials: "include" });
    if (!response.ok) return [];
    const config = (await response.json()) as HeadlessConfig;
    return (config.data?.socialaccount?.providers ?? [])
      .filter((provider) => provider.flows?.includes("provider_redirect") ?? true)
      .map((provider) => provider.id)
      .filter((id): id is SocialProvider => id === "google" || id === "facebook");
  } catch {
    return [];
  }
}

/**
 * Start Google or Facebook sign-in.
 *
 * This is a real form submission, not a fetch: the browser has to leave the
 * site for the provider's consent screen and come back. allauth's headless
 * endpoint reads form fields (not JSON) and checks the CSRF token, then
 * redirects to the provider; afterwards the provider returns the customer to
 * `/auth/callback`, which reads the session the backend has just created.
 */
export async function startSocialLogin(provider: SocialProvider, next = "/"): Promise<void> {
  await ensureCsrfCookie();

  const callback = new URL("/auth/callback", window.location.origin);
  callback.searchParams.set("next", next);

  const fields: Record<string, string> = {
    provider,
    process: "login",
    callback_url: callback.toString(),
    csrfmiddlewaretoken: readCsrfToken(),
  };

  const form = document.createElement("form");
  form.method = "POST";
  form.action = `${API_ORIGIN}/_allauth/browser/v1/auth/provider/redirect`;
  form.style.display = "none";
  for (const [name, value] of Object.entries(fields)) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    form.appendChild(input);
  }
  document.body.appendChild(form);
  form.submit();
}
