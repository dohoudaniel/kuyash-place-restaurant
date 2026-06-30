"use client";

import { useState } from "react";
import { Truck, Clock, Calendar, MapPin, Phone, User } from "lucide-react";
import type { DeliveryData } from "./DeliveryStep";

interface DeliveryStepCompactProps {
  onNext: (data: DeliveryData) => void;
  initialData: DeliveryData | null;
  deliveryOption: "standard" | "express" | "scheduled";
  onDeliveryOptionChange: (option: "standard" | "express" | "scheduled") => void;
  scheduledTime: string;
  onScheduledTimeChange: (time: string) => void;
}

export default function DeliveryStepCompact({
  onNext,
  initialData,
  deliveryOption,
  onDeliveryOptionChange,
  scheduledTime,
  onScheduledTimeChange,
}: DeliveryStepCompactProps) {
  const [formData, setFormData] = useState<DeliveryData>(
    initialData || {
      fullName: "",
      phone: "",
      address: "",
      city: "",
      state: "",
      zipCode: "",
      deliveryNotes: "",
    }
  );

  const [errors, setErrors] = useState<Partial<Record<keyof DeliveryData, string>>>({});

  const validate = () => {
    const newErrors: Partial<Record<keyof DeliveryData, string>> = {};

    if (!formData.fullName.trim()) newErrors.fullName = "Required";
    if (!formData.phone.trim()) newErrors.phone = "Required";
    if (!formData.address.trim()) newErrors.address = "Required";
    if (!formData.city.trim()) newErrors.city = "Required";
    if (!formData.state.trim()) newErrors.state = "Required";
    if (!formData.zipCode.trim()) newErrors.zipCode = "Required";

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) {
      onNext(formData);
    }
  };

  const deliveryOptions = [
    { value: "standard", label: "Standard", time: "30-45 min", price: "₦5.00", icon: Truck },
    { value: "express", label: "Express", time: "15-20 min", price: "₦10.00", icon: Clock },
    { value: "scheduled", label: "Schedule", time: "Pick time", price: "₦5.00", icon: Calendar },
  ];

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <h2 className="font-black text-xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Delivery Information
        </h2>

        {/* Delivery Options */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          {deliveryOptions.map((option) => {
            const Icon = option.icon;
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => onDeliveryOptionChange(option.value as any)}
                className="p-3 rounded-lg border-2 transition-all text-center hover:shadow-md"
                style={{
                  borderColor: deliveryOption === option.value ? "var(--red)" : "var(--gray-mid)",
                  background: deliveryOption === option.value ? "rgba(217,4,41,0.05)" : "white",
                }}
              >
                <Icon className="w-5 h-5 mx-auto mb-2" style={{ color: deliveryOption === option.value ? "var(--red)" : "var(--text-muted)" }} />
                <p className="font-bold text-xs" style={{ color: "var(--black)" }}>{option.label}</p>
                <p className="text-[10px] mt-1" style={{ color: "var(--text-muted)" }}>{option.time}</p>
                <p className="text-xs font-bold mt-1" style={{ color: "var(--red)" }}>{option.price}</p>
              </button>
            );
          })}
        </div>

        {deliveryOption === "scheduled" && (
          <div className="mb-6 p-4 rounded-lg" style={{ background: "rgba(217,4,41,0.05)" }}>
            <label className="block text-xs font-bold mb-2" style={{ color: "var(--black)" }}>
              <Calendar className="w-4 h-4 inline mr-1" />
              Schedule Delivery Time
            </label>
            <input
              type="datetime-local"
              value={scheduledTime}
              onChange={(e) => onScheduledTimeChange(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border outline-none transition-colors focus:border-red-500"
              style={{ borderColor: "var(--gray-mid)" }}
              min={new Date().toISOString().slice(0, 16)}
            />
          </div>
        )}

        {/* Form Fields - 2 Column Grid */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-bold mb-1.5" style={{ color: "var(--black)" }}>
              <User className="w-3 h-3 inline mr-1" />
              Full Name
            </label>
            <input
              type="text"
              value={formData.fullName}
              onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-lg border outline-none transition-colors focus:border-red-500"
              style={{ borderColor: errors.fullName ? "#ef4444" : "var(--gray-mid)" }}
              placeholder="John Doe"
            />
          </div>

          <div>
            <label className="block text-xs font-bold mb-1.5" style={{ color: "var(--black)" }}>
              <Phone className="w-3 h-3 inline mr-1" />
              Phone Number
            </label>
            <input
              type="tel"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-lg border outline-none transition-colors focus:border-red-500"
              style={{ borderColor: errors.phone ? "#ef4444" : "var(--gray-mid)" }}
              placeholder="+234 800 000 0000"
            />
          </div>

          <div className="col-span-2">
            <label className="block text-xs font-bold mb-1.5" style={{ color: "var(--black)" }}>
              <MapPin className="w-3 h-3 inline mr-1" />
              Street Address
            </label>
            <input
              type="text"
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-lg border outline-none transition-colors focus:border-red-500"
              style={{ borderColor: errors.address ? "#ef4444" : "var(--gray-mid)" }}
              placeholder="123 Main Street, Apt 4B"
            />
          </div>

          <div>
            <label className="block text-xs font-bold mb-1.5" style={{ color: "var(--black)" }}>City</label>
            <input
              type="text"
              value={formData.city}
              onChange={(e) => setFormData({ ...formData, city: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-lg border outline-none transition-colors focus:border-red-500"
              style={{ borderColor: errors.city ? "#ef4444" : "var(--gray-mid)" }}
              placeholder="Lagos"
            />
          </div>

          <div>
            <label className="block text-xs font-bold mb-1.5" style={{ color: "var(--black)" }}>State</label>
            <input
              type="text"
              value={formData.state}
              onChange={(e) => setFormData({ ...formData, state: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-lg border outline-none transition-colors focus:border-red-500"
              style={{ borderColor: errors.state ? "#ef4444" : "var(--gray-mid)" }}
              placeholder="Lagos State"
            />
          </div>

          <div className="col-span-2">
            <label className="block text-xs font-bold mb-1.5" style={{ color: "var(--black)" }}>Zip Code</label>
            <input
              type="text"
              value={formData.zipCode}
              onChange={(e) => setFormData({ ...formData, zipCode: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-lg border outline-none transition-colors focus:border-red-500"
              style={{ borderColor: errors.zipCode ? "#ef4444" : "var(--gray-mid)" }}
              placeholder="100001"
            />
          </div>

          <div className="col-span-2">
            <label className="block text-xs font-bold mb-1.5" style={{ color: "var(--black)" }}>
              Delivery Notes (Optional)
            </label>
            <textarea
              value={formData.deliveryNotes}
              onChange={(e) => setFormData({ ...formData, deliveryNotes: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-lg border outline-none transition-colors focus:border-red-500 resize-none"
              style={{ borderColor: "var(--gray-mid)" }}
              rows={2}
              placeholder="Ring doorbell twice, leave at door..."
            />
          </div>
        </div>
      </div>

      <button
        type="submit"
        className="w-full px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all hover:opacity-90"
        style={{ background: "var(--red)" }}
      >
        Continue to Payment
      </button>
    </form>
  );
}
