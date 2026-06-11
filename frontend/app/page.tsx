import HeroSection from "@/components/hero/HeroSection";
import StatsSection from "@/components/stats/StatsSection";
import MenuSection from "@/components/menu/MenuSection";
import WhyChooseUs from "@/components/why/WhyChooseUs";
import Footer from "@/components/layout/Footer";
import ChatButton from "@/components/ui/ChatButton";

export default function Home() {
  return (
    <main>
      <HeroSection />
      <StatsSection />
      <MenuSection />
      <WhyChooseUs />
      <Footer />
      <ChatButton />
    </main>
  );
}
