import { create } from "zustand";

export interface PromoCode {
  code: string;
  type: "percentage" | "fixed" | "freeDelivery";
  value: number;
  minOrderValue?: number;
  maxDiscount?: number;
  expiryDate?: string;
  usageLimit?: number;
  usedCount?: number;
  description: string;
}

interface PromoStore {
  appliedPromo: PromoCode | null;
  availablePromos: PromoCode[];
  applyPromo: (code: string, orderTotal: number) => { success: boolean; message: string; discount: number };
  removePromo: () => void;
  getAppliedPromo: () => PromoCode | null;
  calculateDiscount: (orderTotal: number) => number;
  initializePromos: () => void;
}

// Mock promo codes - in real app, these would come from backend
const AVAILABLE_PROMOS: PromoCode[] = [
  {
    code: "WELCOME10",
    type: "percentage",
    value: 10,
    minOrderValue: 20,
    maxDiscount: 10,
    description: "10% off your first order (max ₦10)",
  },
  {
    code: "SAVE500",
    type: "fixed",
    value: 5,
    minOrderValue: 30,
    description: "₦5 off orders over ₦30",
  },
  {
    code: "FREEDEL",
    type: "freeDelivery",
    value: 0,
    minOrderValue: 25,
    description: "Free delivery on orders over ₦25",
  },
  {
    code: "MEGA20",
    type: "percentage",
    value: 20,
    minOrderValue: 50,
    maxDiscount: 20,
    description: "20% off orders over ₦50 (max ₦20)",
  },
  {
    code: "FLAT15",
    type: "fixed",
    value: 15,
    minOrderValue: 100,
    description: "₦15 off orders over ₦100",
  },
];

export const usePromoStore = create<PromoStore>((set, get) => ({
  appliedPromo: null,
  availablePromos: [],

  initializePromos: () => {
    set({ availablePromos: AVAILABLE_PROMOS });
  },

  applyPromo: (code, orderTotal) => {
    const promos = get().availablePromos;
    const promo = promos.find((p) => p.code.toLowerCase() === code.toLowerCase());

    if (!promo) {
      return { success: false, message: "Invalid promo code", discount: 0 };
    }

    if (promo.minOrderValue && orderTotal < promo.minOrderValue) {
      return {
        success: false,
        message: `Minimum order value of ₦${promo.minOrderValue.toFixed(2)} required`,
        discount: 0,
      };
    }

    if (promo.expiryDate && new Date(promo.expiryDate) < new Date()) {
      return { success: false, message: "Promo code has expired", discount: 0 };
    }

    if (promo.usageLimit && promo.usedCount && promo.usedCount >= promo.usageLimit) {
      return { success: false, message: "Promo code usage limit reached", discount: 0 };
    }

    let discount = 0;
    if (promo.type === "percentage") {
      discount = (orderTotal * promo.value) / 100;
      if (promo.maxDiscount && discount > promo.maxDiscount) {
        discount = promo.maxDiscount;
      }
    } else if (promo.type === "fixed") {
      discount = promo.value;
    }

    set({ appliedPromo: promo });
    return { success: true, message: "Promo code applied successfully!", discount };
  },

  removePromo: () => {
    set({ appliedPromo: null });
  },

  getAppliedPromo: () => {
    return get().appliedPromo;
  },

  calculateDiscount: (orderTotal) => {
    const promo = get().appliedPromo;
    if (!promo) return 0;

    if (promo.type === "percentage") {
      let discount = (orderTotal * promo.value) / 100;
      if (promo.maxDiscount && discount > promo.maxDiscount) {
        discount = promo.maxDiscount;
      }
      return discount;
    } else if (promo.type === "fixed") {
      return promo.value;
    }

    return 0;
  },
}));
