"use client";

import { motion } from "framer-motion";

export default function HeroImage() {
  return (
    <>
      {/* Desktop — fills entire right panel top to bottom */}
      <div className="absolute inset-0 overflow-hidden">
        {/* Food image — dark background pizza, full bleed */}
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage:
              "url('https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=1400&q=95')",
            backgroundPosition: "center center",
            backgroundSize: "cover",
          }}
        />

        {/* Very subtle left fade to blend into black left panel */}
        <div
          className="absolute inset-y-0 left-0 pointer-events-none"
          style={{
            width: "120px",
            background: "linear-gradient(to right, #0d0d0d 0%, transparent 100%)",
          }}
        />

        {/* Floating ingredients */}
        <motion.div
          className="absolute z-20 text-5xl drop-shadow-2xl"
          style={{ top: "8%", right: "8%" }}
          animate={{ y: [0, -14, 0] }}
          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
          aria-hidden="true"
        >
          🍅
        </motion.div>
        <motion.div
          className="absolute z-20 text-4xl drop-shadow-2xl"
          style={{ top: "5%", right: "35%" }}
          animate={{ y: [0, -10, 0] }}
          transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut", delay: 0.4 }}
          aria-hidden="true"
        >
          🧄
        </motion.div>
        <motion.div
          className="absolute z-20 text-3xl drop-shadow-2xl"
          style={{ top: "3%", right: "5%" }}
          animate={{ y: [0, -8, 0] }}
          transition={{ duration: 2.8, repeat: Infinity, ease: "easeInOut", delay: 0.8 }}
          aria-hidden="true"
        >
          🌿
        </motion.div>
        <motion.div
          className="absolute z-20 text-4xl drop-shadow-2xl"
          style={{ bottom: "20%", right: "5%" }}
          animate={{ y: [0, -12, 0] }}
          transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut", delay: 1.2 }}
          aria-hidden="true"
        >
          🍅
        </motion.div>
      </div>

      {/* Mobile food image */}
      <div
        className="lg:hidden w-full relative overflow-hidden"
        style={{ height: "320px", background: "#0d0d0d" }}
      >
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage:
              "url('https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=900&q=85')",
          }}
        />
        <div
          className="absolute inset-0"
          style={{
            background: "linear-gradient(to top, rgba(13,13,13,0.9) 0%, transparent 60%)",
          }}
        />
      </div>
    </>
  );
}
