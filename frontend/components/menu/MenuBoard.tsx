"use client";

import { useState } from "react";

const BOARD_CATEGORIES = [
  {
    slug: "special-combo",
    label: "SPECIAL COMBO",
    items: [
      { name: "Happy Lunch Combo", description: "Burger, Coke, Fries, Chicken Nuggets", price: "₦79.00" },
      { name: "Pesto's Combo", description: "Bacon Buger M, Coke M, Fries", price: "₦65.00" },
      { name: "Weekend Combo", description: "Burger, Coke, Fries, Chicken Nuggets", price: "₦89.00" },
      { name: "Family Combo", description: "Bacon Buger M, Coke M, Fries", price: "₦69.00" },
      { name: "Kid's Combo", description: "Bacon Buger M, Coke M, Fries", price: "₦49.00" },
    ],
  },
  {
    slug: "snacks",
    label: "SPECIAL COMBO",
    items: [
      { name: "Loaded Fries", description: "Seasoned fries, cheese sauce, jalapeños", price: "₦19.00" },
      { name: "Onion Rings", description: "Crispy golden onion rings", price: "₦15.00" },
      { name: "Mozzarella Sticks", description: "6 pieces with marinara sauce", price: "₦22.00" },
      { name: "Chicken Wings", description: "6 pieces, choice of sauce", price: "₦29.00" },
      { name: "Nachos", description: "Chips, cheese, salsa, sour cream", price: "₦25.00" },
    ],
  },
];

const BURGERS = [
  { name: "Bacon Burger", description: "Chicken breast, cheddar wrapped in a crispy", price: "₦79.00" },
  { name: "Double Cheese Burger", description: "Double Cheesy Burger, Size M, L, XL", price: "₦29.00 - ₦49.00" },
  { name: "Crunchy Cheese Burger", description: "Crunchy Cheesy Burger, Size M, L, XL", price: "₦39.00 - ₦59.00" },
  { name: "Black Mushroom Burger", description: "Black crunchy, mushroom, seafood", price: "₦45.00" },
  { name: "Chicken Cheese Burger", description: "Chicken Cheese Burger, Size M, L, XL", price: "₦49.00" },
  { name: "BeefSteak Cheese Burger", description: "BeeftSteak Cheese Burger, Size M, L, XL", price: "₦59.00" },
  { name: "Seafood Burger", description: "Seafood Burger", price: "₦52.00" },
  { name: "Classic Burger", description: "Classica Burger,", price: "₦29.00" },
  { name: "Breakfast Bacone Burger", description: "Breakfast Burger", price: "₦15.00" },
];

function DotLeader() {
  return (
    <span
      className="flex-1 mx-2"
      style={{
        borderBottom: "2px dotted rgba(255,255,255,0.35)",
        marginBottom: "6px",
        minWidth: "24px",
      }}
    />
  );
}

export default function MenuBoard() {
  const [activeIndex, setActiveIndex] = useState(0);

  const current = BOARD_CATEGORIES[activeIndex];
  const canPrev = activeIndex > 0;
  const canNext = activeIndex < BOARD_CATEGORIES.length - 1;

  return (
    <section
      className="relative w-full overflow-hidden"
      style={{ background: "#111", minHeight: "600px" }}
    >
      {/* Dark wood texture overlay */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage: `
            repeating-linear-gradient(
              90deg,
              transparent,
              transparent 2px,
              rgba(0,0,0,0.18) 2px,
              rgba(0,0,0,0.18) 4px
            ),
            repeating-linear-gradient(
              180deg,
              transparent,
              transparent 40px,
              rgba(255,255,255,0.015) 40px,
              rgba(255,255,255,0.015) 42px
            )
          `,
          background: "linear-gradient(160deg, #1a1a1a 0%, #0d0d0d 40%, #111 70%, #0a0a0a 100%)",
        }}
      />

      {/* White brush stroke at top */}
      <div className="absolute top-0 left-0 right-0 z-10" style={{ height: "60px", overflow: "hidden" }}>
        <svg viewBox="0 0 1400 60" preserveAspectRatio="none" width="100%" height="100%">
          <path
            d="M0,0 L1400,0 L1400,18 Q1100,52 800,28 Q500,8 200,38 Q80,48 0,32 Z"
            fill="white"
          />
          <path
            d="M0,0 L1400,0 L1400,12 Q1050,42 750,20 Q450,2 150,30 Q60,38 0,22 Z"
            fill="white"
            opacity="0.7"
          />
        </svg>
      </div>

      {/* Food photo zone — top area */}
      <div className="relative z-20 flex justify-center items-end" style={{ height: "280px" }}>
        {/* Basil leaf left */}
        <div
          className="absolute"
          style={{ left: "4%", top: "80px", fontSize: "80px", transform: "rotate(-20deg)", opacity: 0.9 }}
        >
          🌿
        </div>

        {/* Sauce bowl */}
        <div
          className="absolute"
          style={{ left: "18%", top: "30px", fontSize: "90px", transform: "rotate(10deg)", opacity: 0.85 }}
        >
          🥣
        </div>

        {/* Basil leaves center-left */}
        <div
          className="absolute"
          style={{ left: "30%", top: "100px", fontSize: "60px", transform: "rotate(-10deg)", opacity: 0.85 }}
        >
          🌿
        </div>

        {/* Main burger on board center-right */}
        <div
          className="absolute"
          style={{ left: "45%", top: "10px", fontSize: "140px", transform: "rotate(-5deg)", filter: "drop-shadow(0 20px 40px rgba(0,0,0,0.8))" }}
        >
          🍔
        </div>

        {/* Cutting board rope */}
        <div
          className="absolute"
          style={{ right: "8%", top: "60px", fontSize: "70px", transform: "rotate(15deg)", opacity: 0.7 }}
        >
          🪵
        </div>

        {/* Title */}
        <div className="absolute inset-0 flex items-center justify-center" style={{ paddingTop: "20px" }}>
          <h2
            style={{
              fontFamily: "'Bebas Neue', sans-serif",
              fontSize: "clamp(2.2rem, 5vw, 3.8rem)",
              color: "#fff",
              letterSpacing: "0.03em",
              textShadow: "0 4px 24px rgba(0,0,0,0.8), 0 2px 8px rgba(0,0,0,0.9)",
              textAlign: "center",
            }}
          >
            Pesto&apos;s Menu Board
          </h2>
        </div>
      </div>

      {/* Main board content */}
      <div className="relative z-20 flex w-full" style={{ minHeight: "420px" }}>

        {/* Left arrow */}
        <div className="flex items-start justify-center" style={{ width: "64px", paddingTop: "60px" }}>
          <button
            onClick={() => canPrev && setActiveIndex(activeIndex - 1)}
            disabled={!canPrev}
            style={{
              width: "40px",
              height: "40px",
              borderRadius: "50%",
              background: "rgba(255,255,255,0.15)",
              border: "2px solid rgba(255,255,255,0.4)",
              color: "#fff",
              fontSize: "18px",
              cursor: canPrev ? "pointer" : "not-allowed",
              opacity: canPrev ? 1 : 0.4,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "background 0.2s",
            }}
          >
            ‹
          </button>
        </div>

        {/* Left column — Special Combo card */}
        <div className="flex-1 flex flex-col items-center px-4 pb-16" style={{ maxWidth: "520px" }}>
          {/* Dashed border card */}
          <div
            style={{
              border: "2px dashed rgba(255,255,255,0.35)",
              borderRadius: "8px",
              padding: "32px 36px",
              width: "100%",
              maxWidth: "460px",
            }}
          >
            <h3
              style={{
                fontFamily: "'Bebas Neue', sans-serif",
                fontSize: "2rem",
                color: "#fff",
                letterSpacing: "0.08em",
                textAlign: "center",
                marginBottom: "28px",
              }}
            >
              {current.label}
            </h3>

            <div className="flex flex-col gap-5">
              {current.items.map((item) => (
                <div key={item.name}>
                  <div className="flex items-end w-full">
                    <span
                      style={{
                        color: "#fff",
                        fontWeight: 700,
                        fontSize: "1.05rem",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {item.name}
                    </span>
                    <DotLeader />
                    <span
                      style={{
                        color: "#E8A020",
                        fontWeight: 700,
                        fontSize: "1.05rem",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {item.price}
                    </span>
                  </div>
                  <p style={{ color: "rgba(255,255,255,0.5)", fontSize: "0.82rem", marginTop: "2px" }}>
                    {item.description}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Next category label at bottom */}
          {canNext && (
            <div style={{ marginTop: "32px", textAlign: "center" }}>
              <button
                onClick={() => setActiveIndex(activeIndex + 1)}
                style={{
                  fontFamily: "'Bebas Neue', sans-serif",
                  fontSize: "1.6rem",
                  color: "#fff",
                  letterSpacing: "0.1em",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  opacity: 0.85,
                }}
              >
                {BOARD_CATEGORIES[activeIndex + 1].label.replace("SPECIAL COMBO", "SNACKS")}
              </button>
            </div>
          )}
          {!canNext && (
            <div style={{ marginTop: "32px", textAlign: "center" }}>
              <span
                style={{
                  fontFamily: "'Bebas Neue', sans-serif",
                  fontSize: "1.6rem",
                  color: "#fff",
                  letterSpacing: "0.1em",
                  opacity: 0.85,
                }}
              >
                SNACKS
              </span>
            </div>
          )}
        </div>

        {/* Vertical divider */}
        <div
          style={{
            width: "1px",
            background: "rgba(255,255,255,0.12)",
            margin: "0 8px",
            alignSelf: "stretch",
          }}
        />

        {/* Right column — Burgers */}
        <div className="flex-1 flex flex-col px-6 md:px-12 pb-16" style={{ maxWidth: "720px" }}>
          <h3
            style={{
              fontFamily: "'Bebas Neue', sans-serif",
              fontSize: "2.4rem",
              color: "#fff",
              letterSpacing: "0.12em",
              textAlign: "center",
              marginBottom: "28px",
              marginTop: "8px",
            }}
          >
            BURGERS
          </h3>

          <div className="flex flex-col gap-4">
            {BURGERS.map((item) => (
              <div key={item.name}>
                <div className="flex items-end w-full">
                  <span
                    style={{
                      color: "#fff",
                      fontWeight: 700,
                      fontSize: "1rem",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {item.name}
                  </span>
                  <DotLeader />
                  <span
                    style={{
                      color: "#E8A020",
                      fontWeight: 700,
                      fontSize: "1rem",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {item.price}
                  </span>
                </div>
                <p style={{ color: "rgba(255,255,255,0.45)", fontSize: "0.8rem", marginTop: "2px" }}>
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Right arrow spacer */}
        <div style={{ width: "64px" }} />
      </div>
    </section>
  );
}
