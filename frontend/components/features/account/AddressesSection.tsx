"use client";

import { useState } from "react";
import { MapPin, Plus, Edit2, Trash2, Home, Briefcase } from "lucide-react";

interface Address {
  id: string;
  type: "home" | "work" | "other";
  name: string;
  street: string;
  city: string;
  phone: string;
  isDefault: boolean;
}

export default function AddressesSection() {
  const [addresses, setAddresses] = useState<Address[]>([
    {
      id: "1",
      type: "home",
      name: "Home",
      street: "123 Gourmet Street, Victoria Island",
      city: "Lagos, Nigeria",
      phone: "+234 123 456 7890",
      isDefault: true,
    },
    {
      id: "2",
      type: "work",
      name: "Office",
      street: "45 Business Avenue, Ikoyi",
      city: "Lagos, Nigeria",
      phone: "+234 098 765 4321",
      isDefault: false,
    },
  ]);

  const [showAddForm, setShowAddForm] = useState(false);

  const typeIcons = {
    home: Home,
    work: Briefcase,
    other: MapPin,
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-black text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Delivery Addresses
        </h2>
        <button
          onClick={() => setShowAddForm(true)}
          className="px-4 py-2 rounded-lg font-bold text-sm flex items-center gap-2 transition-all hover:opacity-90"
          style={{ background: "var(--red)", color: "white" }}
        >
          <Plus className="w-4 h-4" />
          Add New
        </button>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        {addresses.map((address) => {
          const Icon = typeIcons[address.type];
          return (
            <div
              key={address.id}
              className="bg-white rounded-xl border p-5 transition-all hover:shadow-md"
              style={{ borderColor: address.isDefault ? "var(--red)" : "var(--gray-mid)" }}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center"
                    style={{ background: "var(--red)15" }}
                  >
                    <Icon className="w-5 h-5" style={{ color: "var(--red)" }} />
                  </div>
                  <div>
                    <h3 className="font-black text-base" style={{ color: "var(--black)" }}>
                      {address.name}
                    </h3>
                    {address.isDefault && (
                      <span className="text-xs font-bold" style={{ color: "var(--red)" }}>
                        Default
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    className="w-8 h-8 rounded-lg flex items-center justify-center transition-all hover:bg-gray-100"
                    style={{ border: "1px solid var(--gray-mid)" }}
                  >
                    <Edit2 className="w-4 h-4" style={{ color: "var(--black)" }} />
                  </button>
                  <button
                    className="w-8 h-8 rounded-lg flex items-center justify-center transition-all hover:bg-red-50"
                    style={{ border: "1px solid var(--gray-mid)" }}
                  >
                    <Trash2 className="w-4 h-4" style={{ color: "var(--red)" }} />
                  </button>
                </div>
              </div>

              <div className="space-y-1 text-sm" style={{ color: "var(--text-muted)" }}>
                <p className="font-semibold">{address.street}</p>
                <p>{address.city}</p>
                <p className="font-semibold">{address.phone}</p>
              </div>

              {!address.isDefault && (
                <button
                  onClick={() => {
                    setAddresses((prev) =>
                      prev.map((a) => ({ ...a, isDefault: a.id === address.id }))
                    );
                  }}
                  className="mt-4 w-full px-4 py-2 rounded-lg font-bold text-xs transition-all hover:opacity-80"
                  style={{ background: "var(--gray-light)", color: "var(--black)" }}
                >
                  Set as Default
                </button>
              )}
            </div>
          );
        })}
      </div>

      {showAddForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50">
          <div className="bg-white rounded-xl max-w-md w-full p-6">
            <h3 className="font-black text-xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Add New Address
            </h3>
            {/* Add form fields here */}
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowAddForm(false)}
                className="flex-1 px-4 py-3 rounded-lg font-bold transition-all"
                style={{ background: "var(--gray-light)", color: "var(--black)" }}
              >
                Cancel
              </button>
              <button
                onClick={() => setShowAddForm(false)}
                className="flex-1 px-4 py-3 rounded-lg font-bold transition-all"
                style={{ background: "var(--red)", color: "white" }}
              >
                Save Address
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
