/**
 * Readable names for the generated API types.
 *
 * `schema.d.ts` is generated from the backend's OpenAPI schema — never edit it
 * by hand; run `npm run api:sync`. Add aliases here as screens start using them.
 */
import type { components } from "./schema";

type Schemas = components["schemas"];

// Auth & account
export type CurrentUser = Schemas["CurrentUser"];
export type Session = Schemas["Session"];
export type LoginRequest = Schemas["LoginRequest"];
export type RegisterRequest = Schemas["RegisterRequest"];
export type Profile = Schemas["Profile"];
export type AuthUserResponse = Schemas["AuthUserResponse"];
export type RegisterResponse = Schemas["RegisterResponse"];
export type DetailResponse = Schemas["DetailResponse"];

// Payments
export type SavedPaymentMethod = Schemas["SavedPaymentMethod"];
export type PaymentInitialised = Schemas["PaymentInitialised"];

// Orders
export type OrderStatus = Schemas["OrderStatusEnum"];
export type ReorderResponse = Schemas["ReorderResponse"];

// Content
export type LegalPage = Schemas["LegalPage"];
export type LegalPageSummary = Schemas["LegalPageSummary"];
