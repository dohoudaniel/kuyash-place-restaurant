"use client";

import { useState } from "react";
import { Home, Loader2, MapPin, Phone, User } from "lucide-react";
import { ApiError, api } from "@/lib/api/client";
import type { Address } from "@/lib/api/types";

interface AddressFormProps {
  defaults?: { recipient_name?: string; phone?: string; city?: string; state?: string };
  onSaved: (address: Address) => void;
  onCancel?: () => void;
}

const inputClass = "w-full px-4 py-3 rounded-lg border outline-none transition-colors focus:border-red-500";

type Field = "recipient_name" | "phone" | "street" | "area" | "city" | "state" | "landmark" | "delivery_notes";

/**
 * Adds a delivery address to the signed-in account.
 *
 * Replaces the checkout's "Zip Code" field (Lagos addressing does not use it) with
 * `area`, which is what the backend uses to find the delivery zone, and
 * `landmark`, which riders otherwise phone to ask for.
 */
export default function AddressForm({ defaults, onSaved, onCancel }: AddressFormProps) {
  const [form, setForm] = useState<Record<Field, string> & { label: "home" | "work" | "other" }>({
    recipient_name: defaults?.recipient_name ?? "",
    phone: defaults?.phone ?? "",
    street: "",
    area: "",
    city: defaults?.city ?? "",
    state: defaults?.state ?? "",
    landmark: "",
    delivery_notes: "",
    label: "home",
  });
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);

  const set = (field: Field, value: string) => setForm((current) => ({ ...current, [field]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setSaving(true);
    setErrors({});
    setFormError(null);
    try {
      const address = await api<Address>("/accounts/addresses/", { method: "POST", body: form });
      onSaved(address);
    } catch (err) {
      if (err instanceof ApiError && err.code === "validation_error") setErrors(err.fieldErrors);
      else setFormError(err instanceof ApiError ? err.message : "We couldn't save that address. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const field = (name: Field, label: string, options: { placeholder: string; required?: boolean; icon?: React.ReactNode; type?: string; autoComplete?: string }) => (
    <div>
      <label htmlFor={`address-${name}`} className="flex items-center gap-2 text-sm font-semibold mb-2" style={{ color: "var(--black)" }}>
        {options.icon}
        {label}
        {!options.required && <span className="font-normal" style={{ color: "var(--text-muted)" }}>(Optional)</span>}
      </label>
      <input
        id={`address-${name}`}
        type={options.type ?? "text"}
        required={options.required}
        autoComplete={options.autoComplete}
        value={form[name]}
        onChange={(e) => set(name, e.target.value)}
        placeholder={options.placeholder}
        aria-invalid={Boolean(errors[name])}
        className={inputClass}
        style={{ borderColor: errors[name] ? "var(--red)" : "var(--gray-mid)" }}
      />
      {errors[name] && <p className="text-xs font-semibold mt-1" style={{ color: "var(--red)" }}>{errors[name]}</p>}
    </div>
  );

  const redIcon = (Icon: typeof User) => <Icon className="w-4 h-4" style={{ color: "var(--red)" }} />;

  return (
    <form onSubmit={handleSubmit} className="space-y-4 p-4 rounded-lg" style={{ background: "var(--off-white)" }}>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {field("recipient_name", "Recipient", { placeholder: "Who receives the order", required: true, icon: redIcon(User), autoComplete: "name" })}
        {field("phone", "Phone Number", { placeholder: "+234 800 000 0000", required: true, icon: redIcon(Phone), type: "tel", autoComplete: "tel" })}
      </div>
      {field("street", "Street Address", { placeholder: "House number and street name", required: true, icon: redIcon(MapPin), autoComplete: "address-line1" })}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {field("area", "Area", { placeholder: "e.g. Victoria Island", required: true })}
        {field("city", "City", { placeholder: "City", required: true, autoComplete: "address-level2" })}
        {field("state", "State", { placeholder: "State", required: true, autoComplete: "address-level1" })}
      </div>
      {field("landmark", "Landmark", { placeholder: "e.g. Opposite the filling station" })}
      <div>
        <label htmlFor="address-delivery_notes" className="text-sm font-semibold mb-2 block" style={{ color: "var(--black)" }}>
          Delivery Notes <span className="font-normal" style={{ color: "var(--text-muted)" }}>(Optional)</span>
        </label>
        <textarea
          id="address-delivery_notes"
          value={form.delivery_notes}
          onChange={(e) => set("delivery_notes", e.target.value)}
          placeholder="Gate code, which building, anything the rider should know"
          rows={2}
          className={`${inputClass} resize-none`}
          style={{ borderColor: "var(--gray-mid)" }}
        />
      </div>

      <fieldset>
        <legend className="flex items-center gap-2 text-sm font-semibold mb-2" style={{ color: "var(--black)" }}>
          <Home className="w-4 h-4" style={{ color: "var(--red)" }} />
          Save As
        </legend>
        <div className="flex gap-2">
          {(["home", "work", "other"] as const).map((label) => (
            <button
              key={label}
              type="button"
              role="radio"
              aria-checked={form.label === label}
              onClick={() => setForm((current) => ({ ...current, label }))}
              className="px-4 py-2 rounded-lg text-sm font-semibold capitalize transition-all"
              style={{
                border: `2px solid ${form.label === label ? "var(--red)" : "var(--gray-mid)"}`,
                background: form.label === label ? "rgba(217,4,41,0.05)" : "white",
                color: form.label === label ? "var(--red)" : "var(--black)",
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </fieldset>

      {formError && <p role="alert" className="text-sm font-semibold" style={{ color: "var(--red)" }}>{formError}</p>}

      <div className="flex gap-3">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 px-6 py-3 rounded-full text-sm font-bold transition-all hover:bg-gray-100"
            style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={saving}
          className="flex-1 px-6 py-3 rounded-full text-sm font-bold text-white flex items-center justify-center gap-2 transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: "var(--red)" }}
        >
          {saving && <Loader2 className="w-4 h-4 animate-spin" />}
          Save Address
        </button>
      </div>
    </form>
  );
}
