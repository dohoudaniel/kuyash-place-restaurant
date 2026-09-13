import type { components } from "./schema";

/**
 * Money, as the backend sends it: `{ amount, currency, display }`.
 *
 * `amount` is integer kobo and exists for sorting and comparison only. Render
 * `display`. There is no formatter and no arithmetic in this module on purpose:
 * if a component needs a number the API does not provide, the backend is
 * missing a field — add it there.
 *
 * Aliased from the generated schema rather than written by hand, so a change to
 * the wire format fails the typecheck instead of production.
 */
export type Money = components["schemas"]["Money"];
