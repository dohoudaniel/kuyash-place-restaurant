"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Gift, Star, TrendingUp, Award, CheckCircle, Crown, Loader2 } from "lucide-react";
import { formatDate } from "@/components/features/orders/statusStyles";
import { ApiError } from "@/lib/api/client";
import { fetchLedger, fetchLoyaltyAccount, fetchProgramme, fetchRewards } from "@/lib/api/loyalty";
import type { LedgerEntry, LoyaltyAccount, LoyaltyProgramme, Reward } from "@/lib/api/types";
import { useAuthModalStore } from "@/lib/store/authModalStore";
import { useAuthStore } from "@/lib/store/authStore";
import { useCartStore } from "@/lib/store/cartStore";

/**
 * Kuyash Rewards, from the points ledger.
 *
 * "Join Free Now" used to set `signedUp = true` in component state; the tiers,
 * catalogue and bonuses (including referral and anniversary points nothing ever
 * granted) were copy. Membership is now an account, the numbers come from the
 * server, and a reward is applied to the real cart.
 */
export default function RewardsPage() {
  const authStatus = useAuthStore((state) => state.status);
  const openAuth = useAuthModalStore((state) => state.open);
  const applyReward = useCartStore((state) => state.applyReward);
  const signedIn = authStatus === "authenticated";

  const [programme, setProgramme] = useState<LoyaltyProgramme | null>(null);
  const [rewards, setRewards] = useState<Reward[] | null>(null);
  const [account, setAccount] = useState<LoyaltyAccount | null>(null);
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [busyReward, setBusyReward] = useState<string | null>(null);
  const [message, setMessage] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    fetchProgramme().then((data) => !cancelled && setProgramme(data)).catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  // The catalogue carries affordability once signed in, so it follows auth.
  useEffect(() => {
    if (authStatus === "idle" || authStatus === "loading") return;
    let cancelled = false;
    fetchRewards().then((data) => !cancelled && setRewards(data)).catch(() => !cancelled && setRewards([]));
    if (authStatus === "authenticated") {
      fetchLoyaltyAccount().then((data) => !cancelled && setAccount(data)).catch(() => undefined);
      fetchLedger().then((page) => !cancelled && setLedger(page.results)).catch(() => undefined);
    }
    return () => {
      cancelled = true;
    };
  }, [authStatus, reloadKey]);

  const member = signedIn ? account : null;
  const tiers = programme?.tiers ?? [];
  const birthdayPoints = tiers[0]?.birthday_points ?? 0;

  const redeemReward = async (reward: Reward) => {
    setBusyReward(reward.id);
    setMessage(null);
    try {
      await applyReward(reward.id);
      setMessage({ tone: "ok", text: `${reward.name} is on your cart. Your points are used when you place the order.` });
      setReloadKey((key) => key + 1);
    } catch (err) {
      setMessage({ tone: "error", text: err instanceof ApiError ? err.message : "That reward couldn't be applied. Please try again." });
    } finally {
      setBusyReward(null);
    }
  };

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
            Earn points with every delivered order, move up through the tiers, and spend your points on rewards at checkout.
          </p>
          {!signedIn ? (
            <button
              onClick={() => openAuth("signup", "/rewards")}
              disabled={authStatus === "loading" || authStatus === "idle"}
              className="px-10 py-4 rounded-full font-bold text-lg transition-all hover:opacity-90 disabled:opacity-60"
              style={{ background: "white", color: "var(--red)" }}
            >
              Join Free Now
            </button>
          ) : member ? (
            <div className="inline-block px-8 py-5 rounded-2xl text-left min-w-[18rem]" style={{ background: "rgba(255,255,255,0.2)" }}>
              <div className="flex items-center gap-3 mb-3">
                <CheckCircle className="w-6 h-6" />
                <span className="font-bold">{member.tier ? `${member.tier.name} member` : "Member"} · {member.earn_rate}</span>
              </div>
              <p className="font-black text-4xl" style={{ fontFamily: "var(--font-playfair)" }}>
                {member.points_balance.toLocaleString("en-NG")} <span className="text-lg font-bold">points</span>
              </p>
              {member.next_tier ? (
                <>
                  <div className="h-2 rounded-full mt-4" style={{ background: "rgba(255,255,255,0.3)" }}>
                    <div className="h-2 rounded-full" style={{ background: "white", width: `${member.progress_percent}%` }} />
                  </div>
                  <p className="text-sm mt-2">
                    {member.next_tier.points_to_go.toLocaleString("en-NG")} points to {member.next_tier.name}
                  </p>
                </>
              ) : (
                member.tier && <p className="text-sm mt-2">You&apos;ve reached our top tier.</p>
              )}
            </div>
          ) : (
            <Loader2 className="w-8 h-8 mx-auto animate-spin" aria-label="Loading your points" />
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
                description: `Get ${programme?.base_earn_rate ?? "points"} spent on food, once your order is delivered.`,
              },
              {
                icon: <Gift className="w-12 h-12" style={{ color: "var(--red)" }} />,
                title: "2. Unlock Rewards",
                description: "Apply a reward to your cart. Your points are only used when you place the order.",
              },
              {
                icon: <TrendingUp className="w-12 h-12" style={{ color: "var(--red)" }} />,
                title: "3. Level Up",
                description: "Reach higher tiers to earn more points on every order.",
              },
            ].map((step) => (
              <div key={step.title} className="bg-white rounded-2xl p-8 text-center shadow-sm">
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
        {tiers.length > 0 && (
          <section className="py-12">
            <h2 className="font-black text-3xl sm:text-4xl text-center mb-12" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Membership Tiers
            </h2>
            <div className="grid md:grid-cols-3 gap-6">
              {tiers.map((tier, index) => {
                const next = tiers[index + 1];
                const current = member?.tier?.name === tier.name;
                const benefits = [tier.earn_rate, ...(tier.birthday_points > 0 ? [`Birthday bonus: ${tier.birthday_points} points`] : []), ...tier.benefits];
                return (
                  <div
                    key={tier.name}
                    className="bg-white rounded-2xl p-8 relative"
                    style={{
                      border: current ? "3px solid var(--red)" : "2px solid var(--gray-mid)",
                      transform: current ? "scale(1.05)" : "scale(1)",
                    }}
                  >
                    {current && (
                      <div
                        className="absolute -top-4 left-1/2 -translate-x-1/2 px-6 py-1 rounded-full text-xs font-bold text-white"
                        style={{ background: "var(--red)" }}
                      >
                        YOUR TIER
                      </div>
                    )}

                    <div
                      className="w-16 h-16 rounded-full flex items-center justify-center mb-4 mx-auto"
                      style={{ background: tier.colour + "20" }}
                    >
                      <Award className="w-8 h-8" style={{ color: tier.colour }} />
                    </div>

                    <h3 className="font-black text-2xl text-center mb-2" style={{ fontFamily: "var(--font-playfair)", color: tier.colour }}>
                      {tier.name}
                    </h3>
                    <p className="text-sm text-center mb-6" style={{ color: "var(--text-muted)" }}>
                      {next
                        ? `${tier.min_points.toLocaleString("en-NG")} – ${(next.min_points - 1).toLocaleString("en-NG")} lifetime points`
                        : `${tier.min_points.toLocaleString("en-NG")}+ lifetime points`}
                    </p>

                    <ul className="space-y-3">
                      {benefits.map((benefit) => (
                        <li key={benefit} className="flex items-start gap-3 text-sm">
                          <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: tier.colour }} />
                          <span style={{ color: "var(--black)" }}>{benefit}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Rewards Catalog */}
        <section className="py-12">
          <h2 className="font-black text-3xl sm:text-4xl text-center mb-12" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Redeem Your Points
          </h2>
          {message && (
            <p role={message.tone === "error" ? "alert" : "status"} className="text-center text-sm font-semibold mb-6" style={{ color: message.tone === "error" ? "var(--red)" : "#10b981" }}>
              {message.text}{" "}
              {message.tone === "ok" && <Link href="/cart" className="underline">View cart</Link>}
            </p>
          )}
          {rewards === null ? (
            <div className="flex justify-center" role="status" aria-label="Loading rewards">
              <Loader2 className="w-6 h-6 animate-spin" style={{ color: "var(--red)" }} />
            </div>
          ) : rewards.length === 0 ? (
            <p className="text-center text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
              New rewards are on the way. Keep earning — your points will be ready.
            </p>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {rewards.map((item) => {
                const applied = member?.applied_reward?.id === item.id;
                const detail = [item.description, item.min_order_value ? `Orders from ${item.min_order_value.display}` : ""].filter(Boolean).join(" · ");
                return (
                  <div
                    key={item.id}
                    className="bg-white rounded-xl p-6 text-center transition-all hover:shadow-lg flex flex-col"
                    style={{ border: applied ? "2px solid var(--red)" : "2px solid var(--gray-mid)" }}
                  >
                    <div
                      className="w-12 h-12 rounded-full flex items-center justify-center mb-3 mx-auto"
                      style={{ background: "rgba(217,4,41,0.08)" }}
                    >
                      <Gift className="w-6 h-6" style={{ color: "var(--red)" }} />
                    </div>
                    <div className="font-black text-xl mb-2" style={{ color: "var(--black)" }}>
                      {item.points_cost.toLocaleString("en-NG")} pts
                    </div>
                    <h3 className="font-bold text-base mb-1" style={{ color: "var(--black)" }}>
                      {item.name}
                    </h3>
                    <p className="text-xs flex-1" style={{ color: "var(--text-muted)" }}>
                      {detail || item.reward_type_display}
                    </p>
                    {signedIn && (
                      <div className="mt-4">
                        {applied ? (
                          <p className="text-xs font-bold flex items-center justify-center gap-1" style={{ color: "#10b981" }}>
                            <CheckCircle className="w-4 h-4" /> On your cart
                          </p>
                        ) : !item.in_stock ? (
                          <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>Out of stock</p>
                        ) : item.affordable ? (
                          <button
                            onClick={() => redeemReward(item)}
                            disabled={busyReward !== null}
                            className="w-full py-2 rounded-full text-xs font-bold text-white transition-all hover:opacity-90 disabled:opacity-50"
                            style={{ background: "var(--red)" }}
                          >
                            {busyReward === item.id ? "Applying…" : "Use on My Cart"}
                          </button>
                        ) : (
                          <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
                            {(item.points_short ?? 0).toLocaleString("en-NG")} more points needed
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Your points history */}
        {signedIn && ledger.length > 0 && (
          <section className="py-12 bg-white rounded-2xl px-8 mb-12">
            <h2 className="font-black text-3xl text-center mb-8" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Your Points History
            </h2>
            <ul className="max-w-2xl mx-auto divide-y" style={{ borderColor: "var(--gray-mid)" }}>
              {ledger.map((entry) => (
                <li key={entry.id} className="flex items-center justify-between py-3 gap-4">
                  <div>
                    <p className="text-sm font-bold" style={{ color: "var(--black)" }}>{entry.description}</p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>{entry.entry_type_display} · {formatDate(entry.created_at, "short")}</p>
                  </div>
                  <span className="font-black text-base whitespace-nowrap" style={{ color: entry.points >= 0 ? "#10b981" : "var(--red)" }}>
                    {entry.points > 0 ? "+" : ""}{entry.points.toLocaleString("en-NG")} pts
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Bonus Ways to Earn */}
        {birthdayPoints > 0 && (
          <section className="py-12 bg-white rounded-2xl px-8">
            <h2 className="font-black text-3xl text-center mb-10" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Bonus Ways to Earn
            </h2>
            <div className="max-w-xs mx-auto">
              <div className="text-center p-6 rounded-xl" style={{ background: "var(--cream)" }}>
                <div className="flex justify-center mb-3" style={{ color: "var(--red)" }}>
                  <Star className="w-8 h-8" />
                </div>
                <h3 className="font-bold text-base mb-1" style={{ color: "var(--black)" }}>
                  Birthday Bonus
                </h3>
                <div className="font-black text-xl" style={{ color: "var(--red)" }}>
                  +{birthdayPoints.toLocaleString("en-NG")} pts
                </div>
                {member && !member.birthday_on_file && (
                  <Link href="/account" className="inline-block mt-3 text-xs font-bold underline" style={{ color: "var(--red)" }}>
                    Add your birthday
                  </Link>
                )}
              </div>
            </div>
          </section>
        )}

        {/* CTA Section */}
        <section className="py-12">
          <div className="bg-white rounded-2xl p-8 sm:p-12 text-center">
            <h2 className="font-black text-3xl sm:text-4xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Ready to Start Earning?
            </h2>
            <p className="text-base sm:text-lg mb-8 max-w-2xl mx-auto" style={{ color: "var(--text-muted)" }}>
              Every Kuyash Place account is a rewards membership. It&apos;s free, and points start with your first delivered order.
            </p>
            {!signedIn ? (
              <button
                onClick={() => openAuth("signup", "/rewards")}
                className="px-10 py-4 rounded-full font-bold text-lg text-white transition-all hover:opacity-90"
                style={{ background: "var(--red)" }}
              >
                Sign Up for Free
              </button>
            ) : (
              <Link
                href="/menu"
                className="inline-block px-10 py-4 rounded-full font-bold text-lg text-white transition-all hover:opacity-90"
                style={{ background: "var(--red)" }}
              >
                Start Ordering & Earning
              </Link>
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
                a: programme
                  ? `Points expire after ${programme.expiry_inactive_days} days without a delivered order or a redemption. Any order keeps them active.`
                  : "Points expire after a long period without an order or a redemption.",
              },
              {
                q: "Can I combine a reward with a promo code?",
                a: "Yes. A reward and a promo code can both be used on one order, though together they can't take the food total below zero.",
              },
              {
                q: "What happens if my order is cancelled or refunded?",
                a: "Points you earned from it are removed, and points you spent on a reward for it are given back — automatically.",
              },
              {
                q: "Can I transfer points to another person?",
                a: "No. Points belong to your account, but you can always use a reward on an order for friends and family.",
              },
            ].map((faq) => (
              <div key={faq.q} className="bg-white rounded-xl p-6" style={{ border: "2px solid var(--gray-mid)" }}>
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
