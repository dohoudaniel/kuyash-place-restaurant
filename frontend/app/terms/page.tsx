"use client";

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen pt-20 sm:pt-24 pb-12" style={{ background: "var(--gray-light)" }}>
      <div className="container-custom max-w-4xl">
        <div className="bg-white rounded-2xl p-8 sm:p-12 shadow-sm">
          <h1 className="font-black text-4xl sm:text-5xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Terms of Service
          </h1>
          <p className="text-sm mb-8" style={{ color: "var(--text-muted)" }}>
            Last Updated: January 2025
          </p>

          <div className="space-y-8" style={{ color: "var(--black)" }}>
            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                1. Acceptance of Terms
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                By accessing and using Kuyash Place Restaurant's services, including our website, mobile app, and online ordering platform, you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use our services.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                2. Account Registration
              </h2>
              <div className="space-y-3 text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <p>When creating an account, you agree to:</p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>Provide accurate, current, and complete information</li>
                  <li>Maintain the security of your password</li>
                  <li>Notify us immediately of any unauthorized access</li>
                  <li>Be responsible for all activities under your account</li>
                  <li>Not share your account with others</li>
                </ul>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                3. Orders and Payment
              </h2>
              <div className="space-y-3 text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <p><strong>Order Placement:</strong> All orders are subject to acceptance and availability. We reserve the right to refuse or cancel orders for any reason.</p>
                <p><strong>Pricing:</strong> All prices are in Nigerian Naira (₦) and include applicable taxes unless otherwise stated. Prices may change without notice.</p>
                <p><strong>Payment:</strong> Payment must be made at the time of order. We accept credit cards, debit cards, and other payment methods as displayed.</p>
                <p><strong>Delivery Fees:</strong> Delivery charges apply based on location and order value. Minimum order amounts may apply for delivery.</p>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                4. Delivery and Pickup
              </h2>
              <div className="space-y-3 text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <p><strong>Delivery Times:</strong> Estimated delivery times are approximate and not guaranteed. Delays may occur due to weather, traffic, or other unforeseen circumstances.</p>
                <p><strong>Delivery Area:</strong> We deliver to specified areas only. Check our delivery zones before ordering.</p>
                <p><strong>Pickup:</strong> For pickup orders, please arrive during the specified time window. Orders not collected within 30 minutes may be discarded without refund.</p>
                <p><strong>Failed Delivery:</strong> If delivery fails due to incorrect address or unavailability, additional charges may apply for redelivery.</p>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                5. Cancellations and Refunds
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                Please refer to our <a href="/refunds" className="underline font-bold" style={{ color: "var(--red)" }}>Refund Policy</a> for detailed information about order cancellations, refunds, and our satisfaction guarantee.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                6. Reservations
              </h2>
              <div className="space-y-3 text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <p>When making a reservation, you agree to:</p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>Arrive within 15 minutes of your reservation time</li>
                  <li>Notify us at least 2 hours in advance of cancellations</li>
                  <li>Respect the maximum party size limits</li>
                  <li>Follow our dress code and restaurant policies</li>
                </ul>
                <p className="mt-3">We reserve the right to cancel reservations for repeated no-shows.</p>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                7. Prohibited Activities
              </h2>
              <div className="space-y-3 text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <p>You agree not to:</p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>Use our services for any illegal purpose</li>
                  <li>Violate any local, state, or national laws</li>
                  <li>Harass, abuse, or harm our staff or other customers</li>
                  <li>Attempt to gain unauthorized access to our systems</li>
                  <li>Submit false or fraudulent orders</li>
                  <li>Use automated systems to access our services</li>
                </ul>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                8. Intellectual Property
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                All content on our website, including text, graphics, logos, images, and software, is the property of Kuyash Place Restaurant and protected by copyright and trademark laws. You may not use, reproduce, or distribute our content without written permission.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                9. Limitation of Liability
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                To the maximum extent permitted by law, Kuyash Place Restaurant shall not be liable for any indirect, incidental, special, consequential, or punitive damages resulting from your use of our services. Our total liability shall not exceed the amount paid for your order.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                10. Food Allergies and Dietary Requirements
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                While we make every effort to accommodate dietary requirements and allergies, we cannot guarantee that our food is completely free from allergens. Cross-contamination may occur. Please inform us of any allergies when ordering, and consume at your own risk.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                11. Changes to Terms
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                We reserve the right to modify these Terms of Service at any time. Changes will be effective immediately upon posting. Your continued use of our services constitutes acceptance of the revised terms.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                12. Governing Law
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                These Terms of Service shall be governed by and construed in accordance with the laws of Nigeria. Any disputes shall be resolved in the courts of Lagos State.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                13. Contact Information
              </h2>
              <p className="text-base leading-relaxed mb-4" style={{ color: "var(--text-muted)" }}>
                For questions about these Terms of Service, please contact us:
              </p>
              <div className="p-4 rounded-lg" style={{ background: "var(--cream)" }}>
                <p className="font-bold mb-2">Kuyash Place Restaurant</p>
                <p>Email: legal@kuyashplace.com</p>
                <p>Phone: +234 123 456 7890</p>
                <p>Address: 123 Flavor Street, Lagos, Nigeria</p>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
