"use client";

import { useState } from "react";
import { User, Mail, Phone, Calendar, Save, Edit2 } from "lucide-react";

export default function ProfileSection() {
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    name: "John Doe",
    email: "john@example.com",
    phone: "+234 123 456 7890",
    birthday: "1990-01-15",
  });

  const handleSave = () => {
    setIsEditing(false);
    alert("Profile updated successfully!");
  };

  return (
    <div className="grid lg:grid-cols-3 gap-6">
      {/* Profile Form */}
      <div className="lg:col-span-2 bg-white rounded-xl border p-6" style={{ borderColor: "var(--gray-mid)" }}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-black text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Personal Information
          </h2>
          {!isEditing && (
            <button
              onClick={() => setIsEditing(true)}
              className="px-4 py-2 rounded-lg font-bold text-sm flex items-center gap-2 transition-all hover:opacity-80"
              style={{ background: "var(--gray-light)", color: "var(--black)" }}
            >
              <Edit2 className="w-4 h-4" />
              Edit
            </button>
          )}
        </div>

        <div className="space-y-4">
          {/* Full Name */}
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              <User className="w-4 h-4 inline mr-2" />
              Full Name
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              disabled={!isEditing}
              className="w-full px-4 py-3 rounded-lg border font-semibold disabled:bg-gray-50"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>

          {/* Email & Phone */}
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
                <Mail className="w-4 h-4 inline mr-2" />
                Email
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                disabled={!isEditing}
                className="w-full px-4 py-3 rounded-lg border font-semibold disabled:bg-gray-50"
                style={{ borderColor: "var(--gray-mid)" }}
              />
            </div>
            <div>
              <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
                <Phone className="w-4 h-4 inline mr-2" />
                Phone
              </label>
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                disabled={!isEditing}
                className="w-full px-4 py-3 rounded-lg border font-semibold disabled:bg-gray-50"
                style={{ borderColor: "var(--gray-mid)" }}
              />
            </div>
          </div>

          {/* Birthday */}
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              <Calendar className="w-4 h-4 inline mr-2" />
              Birthday
            </label>
            <input
              type="date"
              value={formData.birthday}
              onChange={(e) => setFormData({ ...formData, birthday: e.target.value })}
              disabled={!isEditing}
              className="w-full px-4 py-3 rounded-lg border font-semibold disabled:bg-gray-50"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>

          {isEditing && (
            <div className="flex gap-3 pt-4">
              <button
                onClick={() => setIsEditing(false)}
                className="px-6 py-3 rounded-lg font-bold transition-all"
                style={{ background: "var(--gray-light)", color: "var(--black)" }}
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="flex-1 px-6 py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-all hover:opacity-90"
                style={{ background: "var(--red)", color: "white" }}
              >
                <Save className="w-4 h-4" />
                Save Changes
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="space-y-4">
        <div className="bg-white rounded-xl border p-6" style={{ borderColor: "var(--gray-mid)" }}>
          <h3 className="font-black text-lg mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Account Status
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm" style={{ color: "var(--text-muted)" }}>Loyalty Points</span>
              <span className="font-black text-lg" style={{ color: "var(--red)" }}>1,250</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm" style={{ color: "var(--text-muted)" }}>Total Spent</span>
              <span className="font-black text-lg" style={{ color: "var(--black)" }}>₦45,600</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm" style={{ color: "var(--text-muted)" }}>Member Tier</span>
              <span className="px-3 py-1 rounded-full text-xs font-bold text-white" style={{ background: "#f59e0b" }}>
                Gold
              </span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border p-6" style={{ borderColor: "var(--gray-mid)" }}>
          <h3 className="font-black text-lg mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Preferences
          </h3>
          <div className="space-y-2 text-sm" style={{ color: "var(--text-muted)" }}>
            <p>✓ Email notifications enabled</p>
            <p>✓ SMS alerts enabled</p>
            <p>✓ Marketing emails subscribed</p>
          </div>
        </div>
      </div>
    </div>
  );
}
