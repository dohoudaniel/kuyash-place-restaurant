"use client";

export default function FooterHours() {
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-[0.18em] mb-5" style={{ color: "var(--red)" }}>
        Opening Hours
      </p>
      <ul className="flex flex-col gap-3 text-sm" style={{ color: "rgba(255,255,255,0.55)" }}>
        <li className="flex justify-between gap-4">
          <span>Mon – Fri</span>
          <span className="text-white">09:00 – 22:00</span>
        </li>
        <li className="flex justify-between gap-4">
          <span>Saturday</span>
          <span className="text-white">09:00 – 23:00</span>
        </li>
        <li className="flex justify-between gap-4">
          <span>Sunday</span>
          <span className="text-white">10:00 – 20:00</span>
        </li>
      </ul>
      <div className="mt-6 text-sm" style={{ color: "rgba(255,255,255,0.55)" }}>
        <p>📞 +1 555 96 36 36</p>
        <p className="mt-1">✉️ hello@kuyashplace.com</p>
      </div>
    </div>
  );
}
