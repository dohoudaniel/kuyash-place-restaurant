/**
 * Share a link to a page on this site: the native share sheet where there is
 * one, otherwise the clipboard.
 */
export async function shareLink(title: string, path: string): Promise<"shared" | "copied" | "dismissed"> {
  const url = `${window.location.origin}${path}`;
  try {
    if (typeof navigator.share === "function") {
      await navigator.share({ title, url });
      return "shared";
    }
    await navigator.clipboard.writeText(url);
    return "copied";
  } catch {
    return "dismissed";
  }
}
