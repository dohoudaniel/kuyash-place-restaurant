import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface HistoricalOrderItem {
  id: string;
  name: string;
  description: string;
  price: number;
  quantity: number;
  imageKey?: string;
  customizations?: {
    extras?: string[];
    substitutions?: string[];
    specialInstructions?: string;
  };
}

export interface HistoricalOrder {
  orderId: string;
  status: "confirmed" | "preparing" | "ontheway" | "delivered" | "cancelled";
  orderDate: string;
  deliveryDate?: string;
  items: HistoricalOrderItem[];
  deliveryAddress: {
    fullName: string;
    phone: string;
    address: string;
    city: string;
    state: string;
    zipCode: string;
    deliveryNotes?: string;
  };
  paymentMethod: "card" | "transfer" | "cash";
  pricing: {
    subtotal: number;
    deliveryFee: number;
    tax: number;
    discount: number;
    tip: number;
    total: number;
  };
  promoCode?: string;
  deliveryOption: "standard" | "express" | "scheduled";
  scheduledTime?: string;
  driverRating?: number;
  orderRating?: number;
  reviewText?: string;
}

interface OrderHistoryStore {
  orders: HistoricalOrder[];
  addOrder: (order: HistoricalOrder) => void;
  updateOrderStatus: (orderId: string, status: HistoricalOrder["status"]) => void;
  addOrderRating: (orderId: string, rating: number, reviewText?: string) => void;
  addDriverRating: (orderId: string, rating: number) => void;
  getOrderById: (orderId: string) => HistoricalOrder | undefined;
  getAllOrders: () => HistoricalOrder[];
  getRecentOrders: (limit?: number) => HistoricalOrder[];
}

export const useOrderHistoryStore = create<OrderHistoryStore>()(
  persist(
    (set, get) => ({
      orders: [],

      addOrder: (order) => {
        set({
          orders: [order, ...get().orders],
        });
      },

      updateOrderStatus: (orderId, status) => {
        set({
          orders: get().orders.map((order) =>
            order.orderId === orderId ? { ...order, status } : order
          ),
        });
      },

      addOrderRating: (orderId, rating, reviewText) => {
        set({
          orders: get().orders.map((order) =>
            order.orderId === orderId
              ? { ...order, orderRating: rating, reviewText }
              : order
          ),
        });
      },

      addDriverRating: (orderId, rating) => {
        set({
          orders: get().orders.map((order) =>
            order.orderId === orderId ? { ...order, driverRating: rating } : order
          ),
        });
      },

      getOrderById: (orderId) => {
        return get().orders.find((order) => order.orderId === orderId);
      },

      getAllOrders: () => {
        return get().orders;
      },

      getRecentOrders: (limit = 5) => {
        return get().orders.slice(0, limit);
      },
    }),
    {
      name: "kuyash-order-history-storage",
    }
  )
);
