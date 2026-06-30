/**
 * Central image registry.
 *
 * HOW TO ADD AN IMAGE
 * -------------------
 * 1. Drop your file into /public/images/<section>/
 * 2. Add a key below pointing to that path (or a remote URL).
 * 3. Reference it anywhere via IMAGES.<key>
 *
 * Sections
 *   hero      – hero section backgrounds / feature shots
 *   menu      – individual dish photos (keyed to MenuItem.imageKey)
 *   brand     – logos, icons, og-images
 */

export const IMAGES = {
  // ── Hero ────────────────────────────────────────────────────────────────────
  hero: {
    /** Main food plate shown in the right panel */
    mainPlate: "/images/hero/main-plate.jpg",
    /** Floating tomato ingredient */
    tomato: "/images/hero/tomato.png",
    /** Floating garlic ingredient */
    garlic: "/images/hero/garlic.png",
  },

  // ── Menu — What's Hot ───────────────────────────────────────────────────────
  menu: {
    signatureGrillPlate:  "/images/menu/signature-grill-plate.jpg",
    fireChickenCombo:     "/images/menu/fire-chicken-combo.jpg",
    chefsSpecialPasta:    "/images/menu/chefs-special-pasta.jpg",

    // Burgers
    classicSmashBurger:   "/images/menu/classic-smash-burger.jpg",
    bbqBaconStack:        "/images/menu/bbq-bacon-stack.jpg",
    spicyJalapenoBurger:  "/images/menu/spicy-jalapeno-burger.jpg",

    // Chicken & Salads
    grilledChickenBreast: "/images/menu/grilled-chicken-breast.jpg",
    caesarSalad:          "/images/menu/caesar-salad.jpg",
    crispyChickenStrips:  "/images/menu/crispy-chicken-strips.jpg",

    // Tacos, Fries & Sides
    streetTacos:          "/images/menu/street-tacos.jpg",
    loadedFries:          "/images/menu/loaded-fries.jpg",
    onionRings:           "/images/menu/onion-rings.jpg",

    // Breakfast
    fullBreakfastPlate:   "/images/menu/full-breakfast-plate.jpg",
    pancakeStack:         "/images/menu/pancake-stack.jpg",
    avocadoToast:         "/images/menu/avocado-toast.jpg",

    // Desserts & Drinks
    chocolateLavaCake:    "/images/menu/chocolate-lava-cake.jpg",
    berryCheesecake:      "/images/menu/berry-cheesecake.jpg",
    classicMilkshake:     "/images/menu/classic-milkshake.jpg",
  },

  // ── Academy ─────────────────────────────────────────────────────────────────
  academy: {
    chef: "/images/chef.png",
  },

  // ── Brand ───────────────────────────────────────────────────────────────────
  brand: {
    logo:   "/images/brand/kuyash.png",
    ogImage: "/images/brand/og-image.jpg",
  },
} as const;

export type ImageKey = keyof typeof IMAGES.menu;
