import type { HeroStat } from "@/lib/types";
import { IMAGES } from "@/lib/assets/images";

export const HERO_STATS: HeroStat[] = [
  { value: "250+", label: "Food items"      },
  { value: "15k+", label: "Happy customers" },
];

export const HERO_OPENING_HOURS = [
  "Mon–Sat: 09:00am – 02:00pm",
  "Sunday: 09:00am – 02:00pm",
];

export const HERO_STARTING_PRICE = "₦7.90";

/** Image used in the hero right panel */
export const HERO_PLATE_IMAGE = IMAGES.hero.mainPlate;
