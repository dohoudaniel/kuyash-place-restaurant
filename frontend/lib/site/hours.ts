import type { OpeningHours, OpeningHoursResponse } from "@/lib/api/types";

const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/** "18:30:00" → "6:30 PM". */
export function formatClock(value: string | null | undefined): string {
  if (!value) return "";
  const [hours, minutes] = value.split(":").map(Number);
  return new Date(2000, 0, 1, hours, minutes).toLocaleTimeString("en-NG", { hour: "numeric", minute: "2-digit" });
}

function dayText(rows: OpeningHours[]): string {
  if (rows.length === 0 || rows.every((row) => row.is_closed)) return "Closed";
  return rows
    .filter((row) => !row.is_closed)
    .sort((a, b) => a.opens_at.localeCompare(b.opens_at))
    .map((row) => `${formatClock(row.opens_at)} – ${formatClock(row.closes_at)}`)
    .join(", ");
}

/** Consecutive days with the same hours, e.g. `[{ days: "Mon – Thu", time: "11:00 AM – 10:00 PM" }]`. */
export function summariseHours(hours: OpeningHours[]): { days: string; time: string }[] {
  const texts = DAY_NAMES.map((_, weekday) => dayText(hours.filter((row) => Number(row.weekday) === weekday)));
  const groups: { start: number; end: number; time: string }[] = [];
  texts.forEach((time, weekday) => {
    const last = groups[groups.length - 1];
    if (last && last.time === time) last.end = weekday;
    else groups.push({ start: weekday, end: weekday, time });
  });
  return groups.map(({ start, end, time }) => ({
    days: start === end ? DAY_NAMES[start] : `${DAY_NAMES[start]} – ${DAY_NAMES[end]}`,
    time,
  }));
}

/** Today's hours in words, honouring a holiday override for today. */
export function todaysHours(data: OpeningHoursResponse, now = new Date()): string {
  const iso = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  const override = data.overrides.find((entry) => entry.date === iso);
  if (override) {
    if (override.is_closed) return override.note ? `Closed today — ${override.note}` : "Closed today";
    return `${formatClock(override.opens_at)} – ${formatClock(override.closes_at)}`;
  }
  // JavaScript counts from Sunday; the backend's Weekday counts from Monday.
  const weekday = (now.getDay() + 6) % 7;
  return dayText(data.hours.filter((row) => Number(row.weekday) === weekday));
}
