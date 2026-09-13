/**
 * Kuyash Academy: courses, classes and enrolments.
 *
 * Course fees are paid through the same providers and verification as food
 * orders. Nothing here sends a price; `expected_amount` is a guard.
 */
import { enrolmentHeaders, rememberEnrolment } from "@/lib/academy/tokens";
import { api, apiBlob } from "./client";
import type { Course, CourseDetail, Enrolment, EnrolmentCreated, EnrolmentPaymentStart, EnrolmentPaymentVerification, ExperienceLevel } from "./types";

export const fetchCourses = () => api<Course[]>("/academy/courses/");

export const fetchCourse = (slug: string) => api<CourseDetail>(`/academy/courses/${encodeURIComponent(slug)}/`);

export interface EnrolInput {
  cohort: string;
  name: string;
  email: string;
  phone: string;
  experience_level: ExperienceLevel;
  payment_method: "card" | "transfer";
  /** Kobo — the fee the student was shown. */
  expected_amount: number;
}

export async function enrol(input: EnrolInput, idempotencyKey: string): Promise<EnrolmentCreated> {
  const created = await api<EnrolmentCreated>("/academy/enrolments/", { method: "POST", body: input, idempotencyKey });
  if (created.guest_token) rememberEnrolment(created.enrolment.reference, created.guest_token);
  return created;
}

export const fetchMyEnrolments = () => api<Enrolment[]>("/academy/enrolments/mine/");

export const fetchEnrolment = (reference: string) =>
  api<Enrolment>(`/academy/enrolments/${encodeURIComponent(reference)}/`, { headers: enrolmentHeaders(reference) });

/** Start (or retry) the card payment. Returns the provider's hosted checkout URL. */
export const payEnrolment = (reference: string) =>
  api<EnrolmentPaymentStart>(`/academy/enrolments/${encodeURIComponent(reference)}/pay/`, {
    method: "POST",
    headers: enrolmentHeaders(reference),
  });

/** Ask the backend to confirm a course payment with the provider. */
export const verifyEnrolmentPayment = (paymentReference: string) =>
  api<EnrolmentPaymentVerification>(`/academy/payments/verify/${encodeURIComponent(paymentReference)}/`);

export const downloadCertificate = (reference: string) =>
  apiBlob(`/academy/enrolments/${encodeURIComponent(reference)}/certificate/`, { headers: enrolmentHeaders(reference) });
