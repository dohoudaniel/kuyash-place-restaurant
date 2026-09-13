/**
 * The open conversation, remembered for this tab only.
 *
 * sessionStorage rather than localStorage: the token reads the transcript, so
 * it should not outlive the visit on a shared computer.
 */
const KEY = "kuyash-chat-session";

export interface StoredChat {
  id: string;
  token: string;
}

export function loadStoredChat(): StoredChat | null {
  try {
    const raw = window.sessionStorage.getItem(KEY);
    if (!raw) return null;
    const value: unknown = JSON.parse(raw);
    if (value && typeof value === "object" && typeof (value as StoredChat).id === "string" && typeof (value as StoredChat).token === "string") {
      return value as StoredChat;
    }
    return null;
  } catch {
    return null;
  }
}

export function storeChat(chat: StoredChat): void {
  try {
    window.sessionStorage.setItem(KEY, JSON.stringify(chat));
  } catch {
    /* private mode: the conversation simply won't survive a reload */
  }
}

export function clearStoredChat(): void {
  try {
    window.sessionStorage.removeItem(KEY);
  } catch {
    /* nothing stored */
  }
}
