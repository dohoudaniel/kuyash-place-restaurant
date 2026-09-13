"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { CheckCircle, Clock, Loader2, XCircle } from "lucide-react";
import { verifyEnrolmentPayment } from "@/lib/api/academy";
import { ApiError } from "@/lib/api/client";

type State = "verifying" | "paid" | "pending" | "failed" | "missing";

const POLL_INTERVAL_MS = 3000;
const MAX_ATTEMPTS = 10;

/**
 * Where the payment provider returns a student. Arriving proves nothing: the
 * backend asks the provider, and only that answer confirms the seat.
 */
function EnrolmentPaymentComplete() {
  const params = useSearchParams();
  const reference = params.get("reference") ?? params.get("tx_ref") ?? params.get("trxref");
  const [state, setState] = useState<State>(reference ? "verifying" : "missing");
  const [enrolmentReference, setEnrolmentReference] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (!reference || started.current) return;
    started.current = true;
    let cancelled = false;
    void (async () => {
      for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
        try {
          const result = await verifyEnrolmentPayment(reference);
          if (cancelled) return;
          setEnrolmentReference(result.enrolment_reference);
          if (result.status === "success") {
            setState("paid");
            return;
          }
          if (result.status !== "pending" && result.status !== "initialised") {
            setState("failed");
            return;
          }
        } catch (err) {
          if (cancelled) return;
          if (err instanceof ApiError && err.status === 404) {
            setState("missing");
            return;
          }
          if (err instanceof ApiError && err.code === "payment_amount_mismatch") {
            setState("failed");
            return;
          }
        }
        await new Promise((resolve) => window.setTimeout(resolve, POLL_INTERVAL_MS));
        if (cancelled) return;
      }
      setState("pending");
    })();
    return () => {
      cancelled = true;
    };
  }, [reference]);

  const content: Record<State, { icon: React.ReactNode; tone: string; title: string; body: string }> = {
    verifying: { icon: <Loader2 className="w-8 h-8 animate-spin" style={{ color: "var(--red)" }} />, tone: "rgba(217,4,41,0.08)", title: "Confirming your payment", body: "We're checking with the payment provider. This usually takes a few seconds." },
    paid: { icon: <CheckCircle className="w-8 h-8" style={{ color: "#10b981" }} />, tone: "rgba(16,185,129,0.1)", title: "You're enrolled!", body: "Your seat is confirmed. We've emailed your class details." },
    pending: { icon: <Clock className="w-8 h-8" style={{ color: "#f59e0b" }} />, tone: "rgba(245,158,11,0.1)", title: "Payment still processing", body: "Your bank hasn't confirmed yet. We'll email you as soon as it does." },
    failed: { icon: <XCircle className="w-8 h-8" style={{ color: "var(--red)" }} />, tone: "rgba(217,4,41,0.08)", title: "Payment not completed", body: "No money was taken. You can try again from your enrollment while your seat is held." },
    missing: { icon: <XCircle className="w-8 h-8" style={{ color: "var(--text-muted)" }} />, tone: "var(--gray-light)", title: "We couldn't find that payment", body: "If you were charged, contact us with your enrollment reference." },
  };
  const view = content[state];

  return (
    <div className="bg-white rounded-xl border p-8 max-w-md w-full text-center" style={{ borderColor: "var(--gray-mid)" }}>
      <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: view.tone }}>
        {view.icon}
      </div>
      <h1 className="font-black text-2xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>{view.title}</h1>
      <p role="status" className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>{view.body}</p>
      {state !== "verifying" && (
        <div className="space-y-3">
          {enrolmentReference && (
            <Link href={`/academy/enrolments/${enrolmentReference}`} className="block w-full px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all hover:opacity-90" style={{ background: "var(--red)" }}>
              View Enrollment
            </Link>
          )}
          <Link href="/academy" className="block w-full px-6 py-3 rounded-full text-sm font-semibold transition-all hover:bg-gray-50" style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}>
            Back to Academy
          </Link>
        </div>
      )}
    </div>
  );
}

export default function EnrolmentPaymentCompletePage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 pt-20" style={{ background: "var(--off-white)" }}>
      <Suspense fallback={<Loader2 className="w-6 h-6 animate-spin" style={{ color: "var(--red)" }} />}>
        <EnrolmentPaymentComplete />
      </Suspense>
    </div>
  );
}
