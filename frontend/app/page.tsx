import HeroSection from "@/components/features/hero";
import StatsSection from "@/components/features/stats";
import MenuSection from "@/components/features/menu";
import WhyChooseUs from "@/components/features/why-choose-us";

export default function Home() {
  return (
    <main>
      <HeroSection />
      <StatsSection />
      <MenuSection />
      <WhyChooseUs />
    </main>
  );
}
