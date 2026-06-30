"use client";

import { useState } from "react";
import { Gift, Star, TrendingUp, Award, CheckCircle, Clock, Percent, Crown } from "lucide-react";

export default function RewardsPage() {
  const [signedUp, setSignedUp] = useState(false);

  return (
    <div className="min-h-screen pt-20 sm:pt-24 pb-12" style={{ background: "var(--gray-light)" }}>
      {/* Hero Section */}
      <section className="py-16 sm:py-24" style={{ background: "var(--red)", color: "white" }}>
        <div className="container-custom text-center">
          <Crown className="w-16 h-16 mx-auto mb-6" />
          <h1 className="font-black text-4xl sm:text-6xl mb-6" style={{ fontFamily: "var(--font-playfair)" }}>
            Kuyash Rewards
          </h1>
          <p className="text-lg sm:text-xl max-w-2xl mx-auto mb-8">
            Earn points with every order, unlock exclusive perks, and enjoy VIP treatment. Because loyal customers deserve to be celebrated!
          </p>
          {!signedUp ? (
            <button
              onClick={() => setSignedUp(true)}
              className="px-10 py-4 rounded-full font-bold text-lg transition-all hover:opacity-90"
              style={{ background: "white", color: "var(--red)" }}
            >
              Join Free Now
            </button>
          ) : (
            <div className="inline-flex items-center gap-3 px-8 py-4 rounded-full" style={{ background: "rgba(255,255,255,0.2)" }}>
              <CheckCircle className="w-6 h-6" />
              <span className="font-bold">You're all set! Start earning rewards today.</span>
            </div>
          )}
        </div>
      </section>

      <div className="container-custom">
        {/* How It Works */}
        <section className="py-12 sm:py-16">
          <h2 className="font-black text-3xl sm:text-4xl text-center mb-12" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            How It Works
          </h2>
          <div className="grid sm:grid-cols-3 gap-8">
            {[
              {
                icon: <Star className="w-12 h-12" style={{ color: "var(--red)" }} />,
                title: "1. Earn Points",
                description: "Get 1 point for every ₦100 spent on orders, dine-in, or catering.",
              },
              {
                icon: <Gift className="w-12 h-12" style={{ color: "var(--red)" }} />,
                title: "2. Unlock Rewards",
                description: "Redeem points for discounts, free items, and exclusive experiences.",
              },
              {
                icon: <TrendingUp className="w-12 h-12" style={{ color: "var(--red)" }} />,
                title: "3. Level Up",
                description: "Rise through tiers to unlock VIP perks and priority service.",
              },
            ].map((step, idx) => (
              <div key={idx} className="bg-white rounded-2xl p-8 text-center shadow-sm">
                <div className="flex justify-center mb-4">{step.icon}</div>
                <h3 className="font-black text-xl mb-3" style={{ color: "var(--black)" }}>
                  {step.title}
                </h3>
                <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Membership Tiers */}
        <section className="py-12">
          <h2 className="font-black text-3xl sm:text-4xl text-center mb-12" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Membership Tiers
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                tier: "Silver",
                color: "#94a3b8",
                requirement: "0 - 499 points",
                benefits: [
                  "Earn 1 point per ₦100",
                  "Birthday reward",
                  "Exclusive member offers",
                  "Early access to new menu items",
                ],
              },
              {
                tier: "Gold",
                color: "#eab308",
                requirement: "500 - 1,999 points",
                benefits: [
                  "Earn 1.5 points per ₦100",
                  "Free delivery on all orders",
                  "Priority reservations",
                  "10% off catering",
                  "Monthly surprise rewards",
                ],
                popular: true,
              },
              {
                tier: "Platinum",
                color: "#9333ea",
                requirement: "2,000+ points",
                benefits: [
                  "Earn 2 points per ₦100",
                  "Complimentary upgrades",
                  "VIP events & tastings",
                  "Personal concierge service",
                  "20% off catering",
                  "Free birthday dinner for 2",
                ],
              },
            ].map((tier) => (
              <div
                key={tier.tier}
                className="bg-white rounded-2xl p-8 relative"
                style={{
                  border: tier.popular ? "3px solid var(--red)" : "2px solid var(--gray-mid)",
                  transform: tier.popular ? "scale(1.05)" : "scale(1)",
                }}
              >
                {tier.popular && (
                  <div
                    className="absolute -top-4 left-1/2 -translate-x-1/2 px-6 py-1 rounded-full text-xs font-bold text-white"
                    style={{ background: "var(--red)" }}
                  >
                    MOST POPULAR
                  </div>
                )}

                <div
                  className="w-16 h-16 rounded-full flex items-center justify-center mb-4 mx-auto"
                  style={{ background: tier.color + "20" }}
                >
                  <Award className="w-8 h-8" style={{ color: tier.color }} />
                </div>

                <h3 className="font-black text-2xl text-center mb-2" style={{ fontFamily: "var(--font-playfair)", color: tier.color }}>
                  {tier.tier}
                </h3>
                <p className="text-sm text-center mb-6" style={{ color: "var(--text-muted)" }}>
                  {tier.requirement}
                </p>

                <ul className="space-y-3">
                  {tier.benefits.map((benefit, idx) => (
                    <li key={idx} className="flex items-start gap-3 text-sm">
                      <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: tier.color }} />
                      <span style={{ color: "var(--black)" }}>{benefit}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        {/* Rewards Catalog */}
        <section className="py-12">
          <h2 className="font-black text-3xl sm:text-4xl text-center mb-12" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Redeem Your Points
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { points: 100, reward: "Free Drink", description: "Any soft drink or juice" },
              { points: 250, reward: "₦500 Off", description: "Your next order" },
              { points: 500, reward: "Free Appetizer", description: "Choose from our selection" },
              { points: 750, reward: "₦1,500 Off", description: "Orders above ₦5,000" },
              { points: 1000, reward: "Free Main Dish", description: "Any item up to ₦3,000" },
              { points: 1500, reward: "₦3,000 Off", description: "Orders above ₦10,000" },
              { points: 2000, reward: "Free Dinner for 2", description: "Up to ₦8,000 value" },
              { points: 3000, reward: "VIP Experience", description: "Private chef's table" },
            ].map((item) => (
              <div
                key={item.points}
                className="bg-white rounded-xl p-6 text-center transition-all hover:shadow-lg"
                style={{ border: "2px solid var(--gray-mid)" }}
              >
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center mb-3 mx-auto"
                  style={{ background: "var(--red)15" }}
                >
                  <Gift className="w-6 h-6" style={{ color: "var(--red)" }} />
                </div>
                <div className="font-black text-xl mb-2" style={{ color: "var(--black)" }}>
                  {item.points} pts
                </div>
                <h3 className="font-bold text-base mb-1" style={{ color: "var(--black)" }}>
                  {item.reward}
                </h3>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Bonus Ways to Earn */}
        <section className="py-12 bg-white rounded-2xl px-8">
          <h2 className="font-black text-3xl text-center mb-10" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Bonus Ways to Earn
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { icon: <Star className="w-8 h-8" />, title: "Birthday Bonus", points: "+500 pts" },
              { icon: <CheckCircle className="w-8 h-8" />, title: "First Order", points: "+200 pts" },
              { icon: <Percent className="w-8 h-8" />, title: "Refer a Friend", points: "+300 pts" },
              { icon: <Clock className="w-8 h-8" />, title: "Anniversary", points: "+1000 pts" },
            ].map((bonus, idx) => (
              <div key={idx} className="text-center p-6 rounded-xl" style={{ background: "var(--cream)" }}>
                <div className="flex justify-center mb-3" style={{ color: "var(--red)" }}>
                  {bonus.icon}
                </div>
                <h3 className="font-bold text-base mb-1" style={{ color: "var(--black)" }}>
                  {bonus.title}
                </h3>
                <div className="font-black text-xl" style={{ color: "var(--red)" }}>
                  {bonus.points}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-12">
          <div className="bg-white rounded-2xl p-8 sm:p-12 text-center">
            <h2 className="font-black text-3xl sm:text-4xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Ready to Start Earning?
            </h2>
            <p className="text-base sm:text-lg mb-8 max-w-2xl mx-auto" style={{ color: "var(--text-muted)" }}>
              Join Kuyash Rewards today and start collecting points on every order. It's free, easy, and delicious!
            </p>
            {!signedUp ? (
              <button
                onClick={() => setSignedUp(true)}
                className="px-10 py-4 rounded-full font-bold text-lg text-white transition-all hover:opacity-90"
                style={{ background: "var(--red)" }}
              >
                Sign Up for Free
              </button>
            ) : (
              <a
                href="/menu"
                className="inline-block px-10 py-4 rounded-full font-bold text-lg text-white transition-all hover:opacity-90"
                style={{ background: "var(--red)" }}
              >
                Start Ordering & Earning
              </a>
            )}
          </div>
        </section>

        {/* FAQ */}
        <section className="py-12">
          <h2 className="font-black text-3xl text-center mb-10" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Frequently Asked Questions
          </h2>
          <div className="max-w-3xl mx-auto space-y-4">
            {[
              {
                q: "Do points expire?",
                a: "Points expire after 12 months of account inactivity. Stay active by ordering at least once a year!",
              },
              {
                q: "Can I combine points with other promotions?",
                a: "Yes! You can use your points along with most promotional offers, unless specifically stated otherwise.",
              },
              {
                q: "How do I check my point balance?",
                a: "Log into your account to view your current points, tier status, and reward history.",
              },
              {
                q: "Can I transfer points to another person?",
                a: "Points are non-transferable, but you can use your points to treat friends and family!",
              },
            ].map((faq, idx) => (
              <div key={idx} className="bg-white rounded-xl p-6" style={{ border: "2px solid var(--gray-mid)" }}>
                <h3 className="font-bold text-base mb-2" style={{ color: "var(--black)" }}>
                  {faq.q}
                </h3>
                <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                  {faq.a}
                </p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
