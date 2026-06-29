import type { MenuCatalog, MenuCategory } from "@/lib/types";

export const MENU_CATEGORIES: MenuCategory[] = [
  { label: "What's Hot",           slug: "whats-hot",     emoji: "🔥" },
  { label: "Burgers",              slug: "burgers",        emoji: "🍔" },
  { label: "Chickens and Salads",  slug: "chicken-salad",  emoji: "🍗" },
  { label: "Tacos, Fries & Sides", slug: "tacos",          emoji: "🌮" },
  { label: "Breakfast",            slug: "breakfast",      emoji: "🥞" },
  { label: "Desserts and Drinks",  slug: "desserts",       emoji: "🍰" },
];

export const MENU_ITEMS: MenuCatalog = {
  "whats-hot": [
    {
      name: "Signature Grill Plate",
      description: "Slow-cooked beef with roasted garlic & herbs",
      price: "₦14.90",
      imageKey: "signatureGrillPlate",
    },
    {
      name: "Fire Chicken Combo",
      description: "Crispy chicken, spicy sauce, pickles & slaw",
      price: "₦12.50",
      imageKey: "fireChickenCombo",
    },
    {
      name: "Chef's Special Pasta",
      description: "House-made fettuccine, truffle cream, parmesan",
      price: "₦13.90",
      imageKey: "chefsSpecialPasta",
    },
  ],

  burgers: [
    {
      name: "Classic Smash Burger",
      description: "Double smash patty, American cheese, pickles",
      price: "₦10.90",
      imageKey: "classicSmashBurger",
    },
    {
      name: "BBQ Bacon Stack",
      description: "Beef patty, streaky bacon, BBQ sauce, onion rings",
      price: "₦13.50",
      imageKey: "bbqBaconStack",
    },
    {
      name: "Spicy Jalapeño Burger",
      description: "Beef patty, jalapeños, pepper jack, chipotle mayo",
      price: "₦11.90",
      imageKey: "spicyJalapenoBurger",
    },
  ],

  "chicken-salad": [
    {
      name: "Grilled Chicken Breast",
      description: "Herb-marinated chicken, lemon butter, greens",
      price: "₦12.90",
      imageKey: "grilledChickenBreast",
    },
    {
      name: "Caesar Salad",
      description: "Romaine, parmesan, house-made croutons, anchovy dressing",
      price: "₦9.90",
      imageKey: "caesarSalad",
    },
    {
      name: "Crispy Chicken Strips",
      description: "5 pieces, served with honey mustard & fries",
      price: "₦11.50",
      imageKey: "crispyChickenStrips",
    },
  ],

  tacos: [
    {
      name: "Street Tacos (3 pcs)",
      description: "Pulled beef, pico de gallo, avocado, lime",
      price: "₦10.90",
      imageKey: "streetTacos",
    },
    {
      name: "Loaded Fries",
      description: "Seasoned fries, cheese sauce, jalapeños, sour cream",
      price: "₦7.50",
      imageKey: "loadedFries",
    },
    {
      name: "Onion Rings",
      description: "Beer-battered, golden crispy, ranch dip",
      price: "₦6.90",
      imageKey: "onionRings",
    },
  ],

  breakfast: [
    {
      name: "Full Breakfast Plate",
      description: "Eggs, bacon, sausage, toast, baked beans",
      price: "₦11.90",
      imageKey: "fullBreakfastPlate",
    },
    {
      name: "Pancake Stack",
      description: "3 fluffy pancakes, maple syrup, fresh berries",
      price: "₦9.50",
      imageKey: "pancakeStack",
    },
    {
      name: "Avocado Toast",
      description: "Sourdough, smashed avo, poached egg, chilli flakes",
      price: "₦10.90",
      imageKey: "avocadoToast",
    },
  ],

  desserts: [
    {
      name: "Chocolate Lava Cake",
      description: "Warm dark chocolate cake, vanilla ice cream",
      price: "₦7.90",
      imageKey: "chocolateLavaCake",
    },
    {
      name: "Berry Cheesecake",
      description: "New York style, mixed berry compote",
      price: "₦8.50",
      imageKey: "berryCheesecake",
    },
    {
      name: "Classic Milkshake",
      description: "Vanilla, chocolate or strawberry — your choice",
      price: "₦6.90",
      imageKey: "classicMilkshake",
    },
  ],
};
