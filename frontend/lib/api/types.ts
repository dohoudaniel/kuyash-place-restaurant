/**
 * Readable names for the generated API types.
 *
 * `schema.d.ts` is generated from the backend's OpenAPI schema — never edit it
 * by hand; run `npm run api:sync`. Add aliases here as screens start using them.
 */
import type { components, operations } from "./schema";

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

// Catalogue
export type Category = Schemas["Category"];
export type DietaryTag = Schemas["DietaryTag"];
export type MenuItemSummary = Schemas["MenuItemList"];
export type MenuItemDetail = Schemas["MenuItemDetail"];
export type ModifierGroup = Schemas["ModifierGroup"];
export type Modifier = Schemas["Modifier"];
export type Variant = Schemas["Variant"];
export type PaginatedMenuItems = Schemas["PaginatedMenuItemListList"];
export type Branch = Schemas["Branch"];

// Cart — derived from operations so they do not depend on component names.
export type Cart = operations["cart_retrieve"]["responses"][200]["content"]["application/json"];
export type CartLine = Cart["items"][number];
export type CartBlocker = Cart["blockers"][number];
export type ItemQuote = operations["cart_quote_create"]["responses"][200]["content"]["application/json"];

// Orders & payments
export type OrderDetail = Schemas["OrderDetail"];
export type OrderLine = OrderDetail["items"][number];
export type OrderTimelineStep = OrderDetail["timeline"][number];
export type OrderRow = Schemas["OrderList"];
export type OrderLineReview = Schemas["OrderLineReview"];

// Reviews
export type Review = Schemas["Review"];
export type OwnReview = Schemas["OwnReview"];
export type PaginatedReviews = Schemas["PaginatedReviewList"];
export type ReviewHelpful = Schemas["ReviewHelpful"];

// Gallery
export type GalleryImage = Schemas["GalleryImage"];
export type GalleryImageDetail = Schemas["GalleryImageDetail"];
export type GalleryCategory = Schemas["GalleryCategoryEnum"];
export type PaymentVerification = Schemas["PaymentVerification"];
export type Address = Schemas["Address"];

// Wishlist
export type Wishlist = Schemas["Wishlist"];

// Site
export type SiteSettings = Schemas["SiteSettings"];
export type OpeningHours = Schemas["OpeningHours"];
export type OpeningHoursResponse = Schemas["OpeningHoursResponse"];
export type Faq = Schemas["Faq"];

// Reservations & catering
export type TableArea = Schemas["TableArea"];
export type Reservation = Schemas["Reservation"];
export type ReservationAvailability = Schemas["ReservationAvailability"];
export type ReservationSlot = Schemas["ReservationSlot"];
export type CateringPackage = Schemas["CateringPackage"];
export type EnquiryCreated = Schemas["EnquiryCreated"];

