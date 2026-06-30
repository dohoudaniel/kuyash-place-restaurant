"use client";

import { useState } from "react";
import { MapPin, Phone, User } from "lucide-react";

interface DeliveryStepProps {
  onNext: (data: DeliveryData) => void;
}

export interface DeliveryData {
  fullName: string;
  phone: string;
  address: string;
  city: string;
  state: string;
  zipCode: string;
  deliveryNotes?: string;
}

export default function DeliveryStep({ onNext }: DeliveryStepProps) {
  const [formData, setFormData] = useState<DeliveryData>({
    fullName: "",
    phone: "",
    address: "",
    city: "",
    state: "",
    zipCode: "",
    deliveryNotes: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onNext(formData);
  };

  const handleChange = (field: keyof DeliveryData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <form onSubmit={handleSubmit} className="max-w-2xl mx-auto">
      <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
        <h2 className="font-black text-xl sm:text-2xl mb-6" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Delivery Information
        </h2>

        <div className="space-y-4">
          {/* Full Name */}
          <div>
            <label className="flex items-center gap-2 text-sm font-semibold mb-2" style={{ color: "var(--black)" }}>
              <User className="w-4 h-4" style={{ color: "var(--red)" }} />
              Full Name
            </label>
            <input
              type="text"
              required
              value={formData.fullName}
              onChange={(e) => handleChange("fullName", e.target.value)}
              placeholder="Enter your full name"
              className="w-full px-4 py-3 rounded-lg border outline-none transition-colors focus:border-red-500"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>

          {/* Phone */}
          <div>
            <label className="flex items-center gap-2 text-sm font-semibold mb-2" style={{ color: "var(--black)" }}>
              <Phone className="w-4 h-4" style={{ color: "var(--red)" }} />
              Phone Number
            </label>
            <input
              type="tel"
              required
              value={formData.phone}
              onChange={(e) => handleChange("phone", e.target.value)}
              placeholder="+234 800 000 0000"
              className="w-full px-4 py-3 rounded-lg border outline-none transition-colors focus:border-red-500"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>

          {/* Address */}
          <div>
            <label className="flex items-center gap-2 text-sm font-semibold mb-2" style={{ color: "var(--black)" }}>
              <MapPin className="w-4 h-4" style={{ color: "var(--red)" }} />
              Street Address
            </label>
            <input
              type="text"
              required
              value={formData.address}
              onChange={(e) => handleChange("address", e.target.value)}
              placeholder="House number and street name"
              className="w-full px-4 py-3 rounded-lg border outline-none transition-colors focus:border-red-500"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>

          {/* City, State, Zip */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-semibold mb-2 block" style={{ color: "var(--black)" }}>
                City
              </label>
              <input
                type="text"
                required
                value={formData.city}
                onChange={(e) => handleChange("city", e.target.value)}
                placeholder="City"
                className="w-full px-4 py-3 rounded-lg border outline-none transition-colors focus:border-red-500"
                style={{ borderColor: "var(--gray-mid)" }}
              />
            </div>

            <div>
              <label className="text-sm font-semibold mb-2 block" style={{ color: "var(--black)" }}>
                State
              </label>
              <input
                type="text"
                required
                value={formData.state}
                onChange={(e) => handleChange("state", e.target.value)}
                placeholder="State"
                className="w-full px-4 py-3 rounded-lg border outline-none transition-colors focus:border-red-500"
                style={{ borderColor: "var(--gray-mid)" }}
              />
            </div>

            <div>
              <label className="text-sm font-semibold mb-2 block" style={{ color: "var(--black)" }}>
                Zip Code
              </label>
              <input
                type="text"
                required
                value={formData.zipCode}
                onChange={(e) => handleChange("zipCode", e.target.value)}
                placeholder="100001"
                className="w-full px-4 py-3 rounded-lg border outline-none transition-colors focus:border-red-500"
                style={{ borderColor: "var(--gray-mid)" }}
              />
            </div>
          </div>

          {/* Delivery Notes */}
          <div>
            <label className="text-sm font-semibold mb-2 block" style={{ color: "var(--black)" }}>
              Delivery Notes (Optional)
            </label>
            <textarea
              value={formData.deliveryNotes}
              onChange={(e) => handleChange("deliveryNotes", e.target.value)}
              placeholder="Any special instructions for delivery..."
              rows={3}
              className="w-full px-4 py-3 rounded-lg border outline-none transition-colors focus:border-red-500 resize-none"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>
        </div>

        <button
          type="submit"
          className="w-full mt-6 px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all duration-200 hover:opacity-90 hover:scale-[1.02] active:scale-95"
          style={{ background: "var(--red)" }}
        >
          Continue to Payment
        </button>
      </div>
    </form>
  );
}
