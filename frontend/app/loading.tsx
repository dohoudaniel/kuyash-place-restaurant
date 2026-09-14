import { Loader2 } from "lucide-react";

/** Shown instantly while a page renders on the server. */
export default function Loading() {
  return (
    <div className="min-h-[70vh] flex items-center justify-center pt-24" role="status" aria-label="Loading">
      <Loader2 className="w-8 h-8 animate-spin" style={{ color: "var(--red)" }} />
    </div>
  );
}
