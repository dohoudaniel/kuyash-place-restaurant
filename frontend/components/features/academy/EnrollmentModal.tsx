"use client";

import { useState } from "react";
import { X, Calendar, Clock, Users, CheckCircle, CreditCard } from "lucide-react";
import type { Course } from "@/app/academy/page";

interface EnrollmentModalProps {
  course: Course;
  onClose: () => void;
}

export default function EnrollmentModal({ course, onClose }: EnrollmentModalProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    experience: "beginner" as "beginner" | "intermediate" | "advanced",
    startDate: "",
    paymentMethod: "card" as "card" | "transfer" | "installment",
  });

  const handleSubmit = () => {
    alert("Enrollment submitted successfully!");
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.8)" }}
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b p-4 sm:p-6 flex items-center justify-between" style={{ borderColor: "var(--gray-mid)" }}>
          <div>
            <h2 className="font-black text-xl sm:text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Enroll in Course
            </h2>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>{course.title}</p>
          </div>
          <button
            onClick={onClose}
            className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:bg-gray-100"
          >
            <X className="w-6 h-6" style={{ color: "var(--black)" }} />
          </button>
        </div>

        <div className="p-4 sm:p-6">
          {/* Progress */}
          <div className="flex items-center gap-3 mb-6">
            <div
              className="flex-1 h-2 rounded-full"
              style={{ background: step >= 1 ? "var(--red)" : "var(--gray-mid)" }}
            />
            <div
              className="flex-1 h-2 rounded-full"
              style={{ background: step >= 2 ? "var(--red)" : "var(--gray-mid)" }}
            />
          </div>

          {step === 1 && (
            <div className="space-y-4">
              {/* Course Summary */}
              <div className="p-4 rounded-xl" style={{ background: "var(--gray-light)" }}>
                <div className="grid grid-cols-3 gap-3">
                  <div className="text-center">
                    <Clock className="w-5 h-5 mx-auto mb-1" style={{ color: "var(--red)" }} />
                    <p className="text-xs font-bold" style={{ color: "var(--black)" }}>{course.duration}</p>
                    <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>{course.sessions} sessions</p>
                  </div>
                  <div className="text-center">
                    <Users className="w-5 h-5 mx-auto mb-1" style={{ color: "var(--red)" }} />
                    <p className="text-xs font-bold" style={{ color: "var(--black)" }}>Small Class</p>
                    <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>Max 15 students</p>
                  </div>
                  <div className="text-center">
                    <CheckCircle className="w-5 h-5 mx-auto mb-1" style={{ color: "var(--red)" }} />
                    <p className="text-xs font-bold" style={{ color: "var(--black)" }}>Certificate</p>
                    <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>Upon completion</p>
                  </div>
                </div>
              </div>

              {/* Personal Info */}
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Full Name *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-4 py-3 rounded-lg border font-semibold"
                    style={{ borderColor: "var(--gray-mid)" }}
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Email *</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-4 py-3 rounded-lg border font-semibold"
                    style={{ borderColor: "var(--gray-mid)" }}
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Phone Number *</label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  className="w-full px-4 py-3 rounded-lg border font-semibold"
                  style={{ borderColor: "var(--gray-mid)" }}
                />
              </div>

              {/* Experience Level */}
              <div>
                <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Your Experience Level</label>
                <div className="grid grid-cols-3 gap-2">
                  {["beginner", "intermediate", "advanced"].map((level) => (
                    <button
                      key={level}
                      onClick={() => setFormData({ ...formData, experience: level as any })}
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

              {/* Start Date */}
              <div>
                <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Preferred Start Date</label>
                <input
                  type="date"
                  value={formData.startDate}
                  onChange={(e) => setFormData({ ...formData, startDate: e.target.value })}
                  min={new Date().toISOString().split("T")[0]}
                  className="w-full px-4 py-3 rounded-lg border font-semibold"
                  style={{ borderColor: "var(--gray-mid)" }}
                />
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              {/* Payment Method */}
              <div>
                <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Payment Method</label>
                <div className="space-y-2">
                  {[
                    { value: "card", label: "Pay Full Amount", desc: `₦${course.price.toLocaleString()} now` },
                    { value: "installment", label: "Pay in Installments", desc: `₦${(course.price / 3).toLocaleString()}/month for 3 months` },
                    { value: "transfer", label: "Bank Transfer", desc: "Get payment details after enrollment" },
                  ].map((method) => (
                    <button
                      key={method.value}
                      onClick={() => setFormData({ ...formData, paymentMethod: method.value as any })}
                      className="w-full p-4 rounded-xl text-left transition-all"
                      style={{
                        background: formData.paymentMethod === method.value ? "var(--red)08" : "var(--gray-light)",
                        border: `2px solid ${formData.paymentMethod === method.value ? "var(--red)" : "var(--gray-mid)"}`,
                      }}
                    >
                      <div className="flex items-center gap-3">
                        <CreditCard className="w-5 h-5" style={{ color: formData.paymentMethod === method.value ? "var(--red)" : "var(--text-muted)" }} />
                        <div>
                          <p className="font-bold text-sm" style={{ color: "var(--black)" }}>{method.label}</p>
                          <p className="text-xs" style={{ color: "var(--text-muted)" }}>{method.desc}</p>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Summary */}
              <div className="p-4 rounded-xl" style={{ background: "var(--gray-light)" }}>
                <h4 className="font-bold text-sm mb-3" style={{ color: "var(--black)" }}>Enrollment Summary</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span style={{ color: "var(--text-muted)" }}>Course Fee</span>
                    <span className="font-bold" style={{ color: "var(--black)" }}>₦{course.price.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span style={{ color: "var(--text-muted)" }}>Registration</span>
                    <span className="font-bold" style={{ color: "#10b981" }}>Free</span>
                  </div>
                  <div className="flex justify-between pt-2" style={{ borderTop: "1px solid var(--gray-mid)" }}>
                    <span className="font-bold" style={{ color: "var(--black)" }}>Total</span>
                    <span className="font-black text-lg" style={{ color: "var(--red)" }}>₦{course.price.toLocaleString()}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Actions */}
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
              onClick={() => (step === 1 ? setStep(2) : handleSubmit())}
              disabled={step === 1 && (!formData.name || !formData.email || !formData.phone)}
              className="flex-1 px-6 py-3 rounded-lg font-bold transition-all disabled:opacity-40"
              style={{ background: "var(--red)", color: "white" }}
            >
              {step === 1 ? "Continue to Payment" : "Complete Enrollment"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
