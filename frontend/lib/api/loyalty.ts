/**
 * Kuyash Rewards. Points come from the server's ledger; nothing here counts
 * them. Applying and removing a reward goes through the cart store, because
 * both return the repriced cart.
 */
import { api } from "./client";
import type { LoyaltyAccount, LoyaltyProgramme, PaginatedLedger, Reward } from "./types";

export const fetchProgramme = () => api<LoyaltyProgramme>("/loyalty/tiers/");

export const fetchRewards = () => api<Reward[]>("/loyalty/rewards/");

export const fetchLoyaltyAccount = () => api<LoyaltyAccount>("/loyalty/account/");

export const fetchLedger = (limit = 10) => api<PaginatedLedger>(`/loyalty/ledger/?limit=${limit}`);
