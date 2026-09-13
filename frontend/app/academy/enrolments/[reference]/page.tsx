"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Calendar, CreditCard, FileDown, GraduationCap, Loader2, XCircle } from "lucide-react";
import { formatDate } from "@/components/features/orders/statusStyles";
import { rememberEnrolment } from "@/lib/academy/tokens";
import { downloadCertificate, fetchEnrolment, payEnrolment } from "@/lib/api/academy";
import { ApiError } from "@/lib/api/client";
import type { Enrolment } from "@/lib/api/types";
import { useAuthModalStore } from "@/lib/store/authModalStore";
import { useAuthStore } from "@/lib/store/authStore";

const STATUS_TONE: Record<Enrolment["status"], string> = {
  pending_payment: "#f59e0b",
  confirmed: "#10b981",
  completed: "#3b82f6",
  cancelled: "var(--text-muted)",
};

function EnrolmentView() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const reference = String(params.reference);
  const authStatus = useAuthStore((state) => state.status);
  const openAuth = useAuthModalStore((state) => state.open);

  const [enrolment, setEnrolment] = useState<Enrolment | null>(null);
  const [loadError, setLoadError] = useState<"not_found" | "network" | null>(null);
  const [busy, setBusy] = useState<"pay" | "certificate" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // An emailed link carries the guest token: keep it, then drop it from the address bar.
  const token = searchParams.get("token");
  useEffect(() => {
    if (!token) return;
    rememberEnrolment(reference, token);
    router.replace(`/academy/enrolments/${reference}`);
  }, [token, reference, router]);

  useEffect(() => {
    if (token || authStatus === "idle" || authStatus === "loading") return;
    let cancelled = false;
    fetchEnrolment(reference)
      .then((data) => {
        if (cancelled) return;
        setEnrolment(data);
        setLoadError(null);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err instanceof ApiError && err.status === 404 ? "not_found" : "network");
      });
    return () => {
      cancelled = true;
    };
  }, [reference, authStatus, token]);

  const pay = async () => {
    setBusy("pay");
    setActionError(null);
    try {
      const payment = await payEnrolment(reference);
      window.location.assign(payment.authorization_url);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "We couldn't start the payment. Please try again.");
      setBusy(null);
    }
  };

  const certificate = async () => {
    setBusy("certificate");
    setActionError(null);
    try {
      const blob = await downloadCertificate(reference);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener");
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "We couldn't download your certificate. Please try again.");
    } finally {
      setBusy(null);
    }
  };

  if (loadError === "not_found") {
    return (
      <div className="bg-white rounded-xl border p-8 max-w-md w-full mx-auto text-center" style={{ borderColor: "var(--gray-mid)" }}>
        <XCircle className="w-12 h-12 mx-auto mb-4" style={{ color: "var(--text-muted)" }} />
        <h1 className="font-black text-2xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>We couldn&apos;t find that enrollment</h1>
        <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
          Open the link in your enrollment email{authStatus !== "authenticated" ? ", or sign in if you enrolled with an account" : ""}.
        </p>
        {authStatus !== "authenticated" && (
          <button onClick={() => openAuth("login", `/academy/enrolments/${reference}`)} className="w-full px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all hover:opacity-90" style={{ background: "var(--red)" }}>
            Sign In
          </button>
        )}
      </div>
    );
  }

  if (!enrolment) {
    return (
      <div className="flex justify-center py-24">
        {loadError === "network" ? (
          <p role="alert" className="text-sm font-semibold" style={{ color: "var(--text-muted)" }}>We couldn&apos;t load your enrollment. Please check your connection.</p>
        ) : (
          <Loader2 className="w-8 h-8 animate-spin" style={{ color: "var(--red)" }} aria-label="Loading enrollment" />
        )}
      </div>
    );
  }

  const cohort = enrolment.cohort;
  const button = "w-full flex items-center justify-center gap-2 py-3 rounded-lg font-semibold text-sm transition-all disabled:opacity-50";

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <Link href="/academy" className="inline-flex items-center gap-2 text-sm font-semibold transition-colors hover:opacity-70" style={{ color: "var(--black)" }}>
        <ArrowLeft className="w-4 h-4" />
        Academy
      </Link>

      <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
        <div className="flex items-start justify-between gap-4 mb-6">
          <div>
            <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>Enrollment {enrolment.reference}</p>
            <h1 className="font-black text-2xl sm:text-3xl mt-1" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              {enrolment.course.title}
            </h1>
            <p className="text-sm mt-1" style={{ color: "var(--red)" }}>with {enrolment.course.instructor}</p>
          </div>
          <span className="px-3 py-1 rounded-full text-xs font-bold text-white whitespace-nowrap" style={{ background: STATUS_TONE[enrolment.status] }}>
            {enrolment.status_display}
          </span>
        </div>

        <div className="grid sm:grid-cols-2 gap-3 mb-6">
          <div className="flex items-center gap-3 p-3 rounded-lg" style={{ background: "var(--gray-light)" }}>
            <Calendar className="w-5 h-5" style={{ color: "var(--red)" }} />
            <div>
              <p className="text-sm font-bold" style={{ color: "var(--black)" }}>{formatDate(cohort.starts_on, "short")} – {formatDate(cohort.ends_on, "short")}</p>
              {cohort.schedule_note && <p className="text-xs" style={{ color: "var(--text-muted)" }}>{cohort.schedule_note}</p>}
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 rounded-lg" style={{ background: "var(--gray-light)" }}>
            <GraduationCap className="w-5 h-5" style={{ color: "var(--red)" }} />
            <div>
              <p className="text-sm font-bold" style={{ color: "var(--black)" }}>{enrolment.paid_at ? `${enrolment.amount_paid.display} paid` : `${enrolment.amount.display} due`}</p>
              <p className="text-xs capitalize" style={{ color: "var(--text-muted)" }}>{enrolment.experience_level} · {enrolment.name}</p>
            </div>
          </div>
        </div>

        {enrolment.status === "pending_payment" && enrolment.hold_expires_at && (
          <p className="text-sm mb-4" style={{ color: "var(--text-muted)" }}>
            Your seat is held until {formatDate(enrolment.hold_expires_at)}.
          </p>
        )}

        {enrolment.bank_transfer && (
          <div className="p-4 rounded-xl text-sm space-y-1 mb-4" style={{ background: "var(--gray-light)" }}>
            <p className="font-bold mb-2" style={{ color: "var(--black)" }}>Transfer {enrolment.amount.display} to:</p>
            <p style={{ color: "var(--black)" }}>{enrolment.bank_transfer.bank_name}</p>
            <p style={{ color: "var(--black)" }}>{enrolment.bank_transfer.account_name}</p>
            <p className="font-black text-lg" style={{ color: "var(--black)" }}>{enrolment.bank_transfer.account_number}</p>
            <p className="text-xs pt-1" style={{ color: "var(--text-muted)" }}>Use {enrolment.reference} as the narration. We&apos;ll email you when it arrives.</p>
          </div>
        )}

        <div className="space-y-3">
          {enrolment.can_pay && (
            <button onClick={pay} disabled={busy !== null} className={`${button} text-white hover:opacity-90`} style={{ background: "var(--red)" }}>
              {busy === "pay" ? <Loader2 className="w-4 h-4 animate-spin" /> : <CreditCard className="w-4 h-4" />}
              Pay {enrolment.amount.display}
            </button>
          )}
          {enrolment.status === "pending_payment" && !enrolment.can_pay && !enrolment.bank_transfer && (
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              This seat hold has expired. <Link href="/academy" className="font-bold underline" style={{ color: "var(--red)" }}>Enroll again</Link> to choose a class.
            </p>
          )}
          {enrolment.certificate_available && (
            <button onClick={certificate} disabled={busy !== null} className={`${button} hover:bg-gray-50`} style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}>
              {busy === "certificate" ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileDown className="w-4 h-4" />}
              Download Certificate
            </button>
          )}
          {actionError && <p role="alert" className="text-sm font-semibold" style={{ color: "var(--red)" }}>{actionError}</p>}
        </div>
      </div>
    </div>
  );
}

export default function EnrolmentPage() {
  return (
    <div className="min-h-screen pt-24 sm:pt-28 pb-16 px-4" style={{ background: "var(--off-white)" }}>
      <Suspense fallback={<div className="flex justify-center py-24"><Loader2 className="w-8 h-8 animate-spin" style={{ color: "var(--red)" }} /></div>}>
        <EnrolmentView />
      </Suspense>
    </div>
  );
}
