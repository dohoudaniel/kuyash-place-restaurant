import AcademyHero from "@/components/academy/AcademyHero";
import Footer from "@/components/layout/Footer";

export const metadata = {
  title: "Kuyash Academy — Master the Art of Fine Cuisine",
  description:
    "Join an elite circle of culinary professionals at Kuyash Academy. World-class training, expert mentors, and a 98% graduate placement rate.",
};

export default function AcademyPage() {
  return (
    <main>
      <AcademyHero />
      <Footer />
    </main>
  );
}
