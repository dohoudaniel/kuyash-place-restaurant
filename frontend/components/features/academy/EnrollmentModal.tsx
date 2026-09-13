"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { X, Calendar, Clock, Users, CheckCircle, CreditCard, Landmark, Loader2 } from "lucide-react";
import { Dialog as DialogPrimitive } from "radix-ui";
import { Dialog, DialogClose, DialogOverlay, DialogPortal, DialogTitle } from "@/components/ui/dialog";
import { formatDate } from "@/components/features/orders/statusStyles";
import { enrol, fetchCourse } from "@/lib/api/academy";
import { ApiError, newIdempotencyKey } from "@/lib/api/client";
import type { Course, CourseDetail, Enrolment, ExperienceLevel } from "@/lib/api/types";
import { useSiteInfo } from "@/lib/site/useSiteInfo";
import { useAuthStore } from "@/lib/store/authStore";

interface EnrollmentModalProps {
  course: Course;
  onClose: () => void;
}

const LEVELS: ExperienceLevel[] = ["beginner", "intermediate", "advanced"];

/**
 * Enrol in a real class and pay for it.
 *
 * The previous form took a free-text start date, offered "Pay in Installments"
 * with no payment plan behind it (ACA-6 — removed, OD-5), and ended in
 * `alert("Enrollment submitted successfully!")`. Now the student picks a
 * scheduled class with real seats, and card payments go through the same
 * provider checkout as food orders.
 */
export default function EnrollmentModal({ course, onClose }: EnrollmentModalProps) {
  const user = useAuthStore((state) => state.user);
  const { branch } = useSiteInfo();
  const bank = branch?.bank_transfer ?? null;

  const [detail, setDetail] = useState<CourseDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [formData, setFormData] = useState({
    name: user?.full_name ?? "",
    email: user?.email ?? "",
    phone: user?.phone ?? "",
    experience: "beginner" as ExperienceLevel,
    cohort: course.next_cohort && course.next_cohort.seats_left > 0 ? course.next_cohort.id : "",
    paymentMethod: "card" as "card" | "transfer",
  });
  const [idempotencyKey] = useState(newIdempotencyKey);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [created, setCreated] = useState<Enrolment | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchCourse(course.slug)
      .then((data) => !cancelled && setDetail(data))
      .catch(() => !cancelled && setLoadError("We couldn't load the class dates. Please try again."));
    return () => {
      cancelled = true;
    };
  }, [course.slug]);

  const shown = detail ?? course;
  const cohorts = detail?.cohorts ?? [];
  const selected = cohorts.find((cohort) => cohort.id === formData.cohort) ?? null;
  const method = formData.paymentMethod === "transfer" && !bank ? "card" : formData.paymentMethod;

  const handleSubmit = async () => {
    if (!selected) return;
    setSubmitting(true);
    setError(null);
    setFieldErrors({});
    try {
      const result = await enrol(
        {
          cohort: selected.id,
          name: formData.name,
          email: formData.email,
          phone: formData.phone,
          experience_level: formData.experience,
          payment_method: method,
          expected_amount: shown.price.amount,
        },
        idempotencyKey
      );
      if (result.payment) {
        window.location.assign(result.payment.authorization_url);
        return;
      }
      setCreated(result.enrolment);
      if (result.payment_error) setError(result.payment_error);
      setStep(3);
    } catch (err) {
      if (err instanceof ApiError) {
        setFieldErrors(err.fieldErrors);
        setError(err.message);
        if (err.code === "cohort_full" || err.code === "price_changed" || err.code === "cohort_unavailable") {
          setStep(1);
          fetchCourse(course.slug).then(setDetail).catch(() => undefined);
        }
      } else {
        setError("We couldn't complete your enrolment. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const canContinue = Boolean(formData.name.trim() && formData.email.trim() && formData.phone.trim() && selected && selected.seats_left > 0);

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogPortal>
        <DialogOverlay className="bg-black/80 supports-backdrop-filter:backdrop-blur-none" />
        <DialogPrimitive.Content
          aria-describedby={undefined}
          className="fixed top-1/2 left-1/2 z-50 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl w-[calc(100%-2rem)] max-w-2xl max-h-[90vh] overflow-y-auto outline-none"
        >
          {/* Header */}
          <div className="sticky top-0 z-10 bg-white border-b p-4 sm:p-6 flex items-center justify-between" style={{ borderColor: "var(--gray-mid)" }}>
            <div>
              <DialogTitle className="font-black text-xl sm:text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                {step === 3 ? "Seat Reserved" : "Enroll in Course"}
              </DialogTitle>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>{course.title}</p>
            </div>
            <DialogClose asChild>
              <button aria-label="Close" className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:bg-gray-100">
                <X className="w-6 h-6" style={{ color: "var(--black)" }} />
              </button>
            </DialogClose>
          </div>

          <div className="p-4 sm:p-6">
            {/* Progress */}
            {step < 3 && (
              <div className="flex items-center gap-3 mb-6">
                <div className="flex-1 h-2 rounded-full" style={{ background: "var(--red)" }} />
                <div className="flex-1 h-2 rounded-full" style={{ background: step >= 2 ? "var(--red)" : "var(--gray-mid)" }} />
              </div>
            )}

            {step === 1 && (
              <div className="space-y-4">
                {/* Course Summary */}
                <div className="p-4 rounded-xl" style={{ background: "var(--gray-light)" }}>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="text-center">
                      <Clock className="w-5 h-5 mx-auto mb-1" style={{ color: "var(--red)" }} />
                      <p className="text-xs font-bold" style={{ color: "var(--black)" }}>{shown.duration_label}</p>
                      <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>{shown.session_count} sessions</p>
                    </div>
                    <div className="text-center">
                      <Users className="w-5 h-5 mx-auto mb-1" style={{ color: "var(--red)" }} />
                      <p className="text-xs font-bold" style={{ color: "var(--black)" }}>{selected ? `Max ${selected.capacity} students` : "Small Class"}</p>
                      <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>{selected ? `${selected.seats_left} seats left` : "Choose a class"}</p>
                    </div>
                    <div className="text-center">
                      <CheckCircle className="w-5 h-5 mx-auto mb-1" style={{ color: "var(--red)" }} />
                      <p className="text-xs font-bold" style={{ color: "var(--black)" }}>Certificate</p>
                      <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>Upon completion</p>
                    </div>
                  </div>
                </div>

                {/* Class */}
                <fieldset>
                  <legend className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Choose a Class *</legend>
                  {loadError && <p role="alert" className="text-sm font-semibold" style={{ color: "var(--red)" }}>{loadError}</p>}
                  {!detail && !loadError && (
                    <div className="flex items-center gap-2" role="status">
                      <Loader2 className="w-4 h-4 animate-spin" style={{ color: "var(--red)" }} />
                      <span className="text-sm" style={{ color: "var(--text-muted)" }}>Loading dates…</span>
                    </div>
                  )}
                  {detail && cohorts.length === 0 && (
                    <p className="text-sm" style={{ color: "var(--text-muted)" }}>No classes are scheduled right now.</p>
                  )}
                  <div className="space-y-2">
                    {cohorts.map((cohort) => {
                      const isSelected = formData.cohort === cohort.id;
                      const full = cohort.seats_left <= 0;
                      return (
                        <button
                          key={cohort.id}
                          type="button"
                          role="radio"
                          aria-checked={isSelected}
                          disabled={full}
                          onClick={() => setFormData({ ...formData, cohort: cohort.id })}
                          className="w-full p-3 rounded-xl text-left transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                          style={{
                            background: isSelected ? "rgba(217,4,41,0.05)" : "var(--gray-light)",
                            border: `2px solid ${isSelected ? "var(--red)" : "var(--gray-mid)"}`,
                          }}
                        >
                          <div className="flex items-center gap-3">
                            <Calendar className="w-5 h-5 shrink-0" style={{ color: isSelected ? "var(--red)" : "var(--text-muted)" }} />
                            <div className="flex-1">
                              <p className="font-bold text-sm" style={{ color: "var(--black)" }}>
                                {formatDate(cohort.starts_on, "short")} – {formatDate(cohort.ends_on, "short")}
                              </p>
                              {cohort.schedule_note && <p className="text-xs" style={{ color: "var(--text-muted)" }}>{cohort.schedule_note}</p>}
                            </div>
                            <span className="text-xs font-bold" style={{ color: full ? "var(--text-muted)" : "var(--red)" }}>
                              {full ? "Full" : `${cohort.seats_left} left`}
                            </span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </fieldset>

                {/* Personal Info */}
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="enrol-name" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Full Name *</label>
                    <input
                      id="enrol-name"
                      type="text"
                      autoComplete="name"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="w-full px-4 py-3 rounded-lg border font-semibold"
                      style={{ borderColor: "var(--gray-mid)" }}
                    />
                    {fieldErrors.name && <p className="text-xs mt-1" style={{ color: "var(--red)" }}>{fieldErrors.name}</p>}
                  </div>
                  <div>
                    <label htmlFor="enrol-email" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Email *</label>
                    <input
                      id="enrol-email"
                      type="email"
                      autoComplete="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className="w-full px-4 py-3 rounded-lg border font-semibold"
                      style={{ borderColor: "var(--gray-mid)" }}
                    />
                    {fieldErrors.email && <p className="text-xs mt-1" style={{ color: "var(--red)" }}>{fieldErrors.email}</p>}
                  </div>
                </div>

                <div>
                  <label htmlFor="enrol-phone" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Phone Number *</label>
                  <input
                    id="enrol-phone"
                    type="tel"
                    autoComplete="tel"
                    placeholder="+234 801 234 5678"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full px-4 py-3 rounded-lg border font-semibold"
                    style={{ borderColor: "var(--gray-mid)" }}
                  />
                  {fieldErrors.phone && <p className="text-xs mt-1" style={{ color: "var(--red)" }}>{fieldErrors.phone}</p>}
                </div>

                {/* Experience Level */}
                <div>
                  <p className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Your Experience Level</p>
                  <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Your experience level">
                    {LEVELS.map((level) => (
                      <button
                        key={level}
                        type="button"
                        role="radio"
                        aria-checked={formData.experience === level}
                        onClick={() => setFormData({ ...formData, experience: level })}
                        className="px-3 py-2 rounded-lg text-sm font-bold capitalize transition-all"
                        style={{
                          background: formData.experience === level ? "var(--red)" : "var(--gray-light)",
                          color: formData.experience === level ? "white" : "var(--black)",
                        }}
                      >
                        {level}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-4">
                {/* Payment Method */}
                <div>
                  <p className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Payment Method</p>
                  <div className="space-y-2">
                    {[
                      { value: "card" as const, label: "Pay by Card", desc: `${shown.price.display} now, on our payment provider's secure page`, icon: CreditCard },
                      ...(bank ? [{ value: "transfer" as const, label: "Bank Transfer", desc: "Your seat is held while you transfer the fee", icon: Landmark }] : []),
                    ].map((option) => {
                      const Icon = option.icon;
                      const isSelected = method === option.value;
                      return (
                        <button
                          key={option.value}
                          type="button"
                          role="radio"
                          aria-checked={isSelected}
                          onClick={() => setFormData({ ...formData, paymentMethod: option.value })}
                          className="w-full p-4 rounded-xl text-left transition-all"
                          style={{
                            background: isSelected ? "rgba(217,4,41,0.05)" : "var(--gray-light)",
                            border: `2px solid ${isSelected ? "var(--red)" : "var(--gray-mid)"}`,
                          }}
                        >
                          <div className="flex items-center gap-3">
                            <Icon className="w-5 h-5" style={{ color: isSelected ? "var(--red)" : "var(--text-muted)" }} />
                            <div>
                              <p className="font-bold text-sm" style={{ color: "var(--black)" }}>{option.label}</p>
                              <p className="text-xs" style={{ color: "var(--text-muted)" }}>{option.desc}</p>
                            </div>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Summary */}
                <div className="p-4 rounded-xl" style={{ background: "var(--gray-light)" }}>
                  <h4 className="font-bold text-sm mb-3" style={{ color: "var(--black)" }}>Enrollment Summary</h4>
                  <div className="space-y-2 text-sm">
                    {selected && (
                      <div className="flex justify-between">
                        <span style={{ color: "var(--text-muted)" }}>Class</span>
                        <span className="font-bold" style={{ color: "var(--black)" }}>
                          {formatDate(selected.starts_on, "short")} – {formatDate(selected.ends_on, "short")}
                        </span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span style={{ color: "var(--text-muted)" }}>Course Fee</span>
                      <span className="font-bold" style={{ color: "var(--black)" }}>{shown.price.display}</span>
                    </div>
                    <div className="flex justify-between pt-2" style={{ borderTop: "1px solid var(--gray-mid)" }}>
                      <span className="font-bold" style={{ color: "var(--black)" }}>Total</span>
                      <span className="font-black text-lg" style={{ color: "var(--red)" }}>{shown.price.display}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {step === 3 && created && (
              <div className="space-y-4" role="status">
                <div className="text-center">
                  <CheckCircle className="w-12 h-12 mx-auto mb-3" style={{ color: "#10b981" }} />
                  <p className="font-bold" style={{ color: "var(--black)" }}>Reference {created.reference}</p>
                  {created.hold_expires_at && (
                    <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
                      Your seat is held until {formatDate(created.hold_expires_at)}.
                    </p>
                  )}
                </div>
                {created.bank_transfer && (
                  <div className="p-4 rounded-xl text-sm space-y-1" style={{ background: "var(--gray-light)" }}>
                    <p className="font-bold mb-2" style={{ color: "var(--black)" }}>Transfer {created.amount.display} to:</p>
                    <p style={{ color: "var(--black)" }}>{created.bank_transfer.bank_name}</p>
                    <p style={{ color: "var(--black)" }}>{created.bank_transfer.account_name}</p>
                    <p className="font-black text-lg" style={{ color: "var(--black)" }}>{created.bank_transfer.account_number}</p>
                    <p className="text-xs pt-1" style={{ color: "var(--text-muted)" }}>Use {created.reference} as the narration. We&apos;ve emailed these details too.</p>
                  </div>
                )}
                <Link
                  href={`/academy/enrolments/${created.reference}`}
                  className="block w-full text-center px-6 py-3 rounded-lg font-bold text-white transition-all hover:opacity-90"
                  style={{ background: "var(--red)" }}
                >
                  View Enrollment
                </Link>
              </div>
            )}

            {error && (
              <p role="alert" className="mt-4 text-sm font-semibold" style={{ color: "var(--red)" }}>{error}</p>
            )}

            {/* Actions */}
            {step < 3 && (
              <div className="flex gap-3 mt-6">
                {step === 2 && (
                  <button
                    onClick={() => setStep(1)}
                    className="px-6 py-3 rounded-lg font-bold transition-all"
                    style={{ background: "var(--gray-light)", color: "var(--black)" }}
                  >
                    Back
                  </button>
                )}
                <button
                  onClick={() => (step === 1 ? setStep(2) : void handleSubmit())}
                  disabled={(step === 1 && !canContinue) || submitting}
                  className="flex-1 px-6 py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-all disabled:opacity-40"
                  style={{ background: "var(--red)", color: "white" }}
                >
                  {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                  {step === 1 ? "Continue to Payment" : method === "card" ? `Pay ${shown.price.display}` : "Reserve My Seat"}
                </button>
              </div>
            )}
          </div>
        </DialogPrimitive.Content>
      </DialogPortal>
    </Dialog>
  );
}
