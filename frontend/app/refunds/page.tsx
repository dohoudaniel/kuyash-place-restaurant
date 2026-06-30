"use client";

export default function RefundPolicyPage() {
  return (
    <div className="min-h-screen pt-20 sm:pt-24 pb-12" style={{ background: "var(--gray-light)" }}>
      <div className="container-custom max-w-4xl">
        <div className="bg-white rounded-2xl p-8 sm:p-12 shadow-sm">
          <h1 className="font-black text-4xl sm:text-5xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Refund & Cancellation Policy
          </h1>
          <p className="text-sm mb-8" style={{ color: "var(--text-muted)" }}>
            Last Updated: January 2025
          </p>

          <div className="space-y-8" style={{ color: "var(--black)" }}>
            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Our Commitment to Quality
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                At Kuyash Place Restaurant, customer satisfaction is our top priority. We stand behind the quality of our food and service. If you're not completely satisfied with your order, we're here to make it right.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Order Cancellations
              </h2>
              <div className="space-y-4">
                <div className="p-4 rounded-lg" style={{ background: "var(--cream)", border: "2px solid var(--red)" }}>
                  <h3 className="font-bold text-lg mb-2" style={{ color: "var(--red)" }}>
                    Before Preparation (Full Refund)
                  </h3>
                  <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                    You may cancel your order for a full refund within 5 minutes of placing it, or before the restaurant begins preparation (whichever comes first). Cancellations can be made through your account or by calling us.
                  </p>
                </div>

                <div className="p-4 rounded-lg" style={{ background: "#fef3c7" }}>
                  <h3 className="font-bold text-lg mb-2" style={{ color: "#f59e0b" }}>
                    During Preparation (Partial Refund)
                  </h3>
                  <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                    If preparation has begun, you may still cancel but a 30% preparation fee will apply. The remaining 70% will be refunded to your original payment method.
                  </p>
                </div>

                <div className="p-4 rounded-lg" style={{ background: "#fee2e2" }}>
                  <h3 className="font-bold text-lg mb-2" style={{ color: "#dc2626" }}>
                    Out for Delivery (No Refund)
                  </h3>
                  <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                    Once your order is out for delivery, cancellations are not accepted. However, you may refuse delivery for quality issues (see below).
                  </p>
                </div>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Refund Eligibility
              </h2>
              <div className="space-y-3 text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <p>You are eligible for a full refund if:</p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>Your order is significantly different from what you ordered</li>
                  <li>Food quality is unsatisfactory (cold, spoiled, or improperly prepared)</li>
                  <li>Items are missing from your order</li>
                  <li>Delivery is more than 60 minutes late from the estimated time</li>
                  <li>You receive someone else's order</li>
                  <li>Food safety concerns are identified</li>
                </ul>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                How to Request a Refund
              </h2>
              <div className="space-y-4 text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <div>
                  <h3 className="font-bold mb-2" style={{ color: "var(--black)" }}>1. Report the Issue Immediately</h3>
                  <p>Contact us within 24 hours of delivery. Provide your order number and photos if applicable.</p>
                </div>
                <div>
                  <h3 className="font-bold mb-2" style={{ color: "var(--black)" }}>2. Review Process</h3>
                  <p>Our team will review your request within 2 business hours. We may ask for additional information.</p>
                </div>
                <div>
                  <h3 className="font-bold mb-2" style={{ color: "var(--black)" }}>3. Resolution</h3>
                  <p>We'll offer a refund, replacement, or store credit based on the situation. Most refunds are processed within 5-7 business days.</p>
                </div>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Refund Methods
              </h2>
              <div className="space-y-3 text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <p><strong>Original Payment Method:</strong> Refunds are typically processed to your original payment method within 5-7 business days.</p>
                <p><strong>Store Credit:</strong> We may offer store credit as an alternative, usually with a 10% bonus for the inconvenience.</p>
                <p><strong>Cash Orders:</strong> Cash refunds will be provided via bank transfer or on your next delivery.</p>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Reservation Cancellations
              </h2>
              <div className="space-y-3 text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <p><strong>More than 24 hours notice:</strong> Free cancellation, no charges.</p>
                <p><strong>2-24 hours notice:</strong> No charge, but repeated late cancellations may affect future booking ability.</p>
                <p><strong>Less than 2 hours or No-show:</strong> A ₦5,000 no-show fee may be charged for special events or large parties.</p>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Non-Refundable Situations
              </h2>
              <div className="space-y-3 text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <p>We cannot provide refunds for:</p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>Change of mind after food preparation has started</li>
                  <li>Subjective taste preferences (too spicy, too mild, etc.) unless you specifically requested otherwise</li>
                  <li>Delays caused by incorrect delivery address provided by customer</li>
                  <li>Customer unavailability during delivery window</li>
                  <li>Partially consumed orders (unless quality issue is evident)</li>
                </ul>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Promotional Items & Gift Cards
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                Free promotional items, complimentary dishes, and gift card purchases are non-refundable. Gift cards do not expire and can be transferred to another person.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Contact Us for Refunds
              </h2>
              <p className="text-base leading-relaxed mb-4" style={{ color: "var(--text-muted)" }}>
                To request a refund or report an issue with your order:
              </p>
              <div className="p-4 rounded-lg" style={{ background: "var(--cream)" }}>
                <p className="font-bold mb-2">Customer Support</p>
                <p>Email: support@kuyashplace.com</p>
                <p>Phone: +234 123 456 7890</p>
                <p>Live Chat: Available on our website 9am - 10pm daily</p>
                <p className="mt-2 text-sm italic">Please have your order number ready when contacting us.</p>
              </div>
            </section>

            <section className="p-6 rounded-xl" style={{ background: "var(--red)", color: "white" }}>
              <h2 className="font-black text-2xl mb-3" style={{ fontFamily: "var(--font-playfair)" }}>
                100% Satisfaction Guarantee
              </h2>
              <p className="text-base leading-relaxed">
                If you're not happy with your meal for any reason, let us know within 24 hours and we'll make it right. Your satisfaction is our priority, and we're committed to delivering excellent food and service every time.
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
