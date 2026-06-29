"use client";

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen pt-20 sm:pt-24 pb-12" style={{ background: "var(--gray-light)" }}>
      <div className="container-custom max-w-4xl">
        <div className="bg-white rounded-2xl p-8 sm:p-12 shadow-sm">
          <h1 className="font-black text-4xl sm:text-5xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Privacy Policy
          </h1>
          <p className="text-sm mb-8" style={{ color: "var(--text-muted)" }}>
            Last Updated: January 2025
          </p>

          <div className="space-y-8" style={{ color: "var(--black)" }}>
            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                1. Information We Collect
              </h2>
              <div className="space-y-3 text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <p>
                  We collect information you provide directly to us when you create an account, place an order, make a reservation, or contact us. This may include:
                </p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>Name, email address, phone number</li>
                  <li>Delivery address and payment information</li>
                  <li>Order history and preferences</li>
                  <li>Communication preferences</li>
                </ul>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                2. How We Use Your Information
              </h2>
              <div className="space-y-3 text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <p>We use the information we collect to:</p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>Process and fulfill your orders and reservations</li>
                  <li>Send order confirmations and updates</li>
                  <li>Improve our menu and services</li>
                  <li>Send promotional communications (with your consent)</li>
                  <li>Respond to your inquiries and support requests</li>
                </ul>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                3. Information Sharing
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                We do not sell your personal information. We may share your information with:
              </p>
              <ul className="list-disc pl-6 space-y-2 mt-3 text-base" style={{ color: "var(--text-muted)" }}>
                <li>Delivery partners to fulfill your orders</li>
                <li>Payment processors to complete transactions</li>
                <li>Service providers who assist in our operations</li>
                <li>Law enforcement when required by law</li>
              </ul>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                4. Data Security
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                We implement appropriate security measures to protect your personal information. However, no method of transmission over the internet is 100% secure. We use encryption for sensitive data and regularly review our security practices.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                5. Your Rights
              </h2>
              <div className="space-y-3 text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <p>You have the right to:</p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>Access and receive a copy of your personal data</li>
                  <li>Correct inaccurate or incomplete information</li>
                  <li>Request deletion of your account and data</li>
                  <li>Opt-out of marketing communications</li>
                  <li>Object to processing of your information</li>
                </ul>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                6. Cookies and Tracking
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                We use cookies and similar technologies to enhance your experience, analyze usage, and personalize content. You can control cookies through your browser settings. See our <a href="/cookies" className="underline font-bold" style={{ color: "var(--red)" }}>Cookie Policy</a> for more details.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                7. Children's Privacy
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                Our services are not directed to individuals under 13. We do not knowingly collect personal information from children. If you believe we have collected information from a child, please contact us immediately.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                8. Changes to This Policy
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                We may update this Privacy Policy from time to time. We will notify you of significant changes by email or through our website. Your continued use of our services constitutes acceptance of the updated policy.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                9. Contact Us
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                If you have questions about this Privacy Policy or our data practices, please contact us:
              </p>
              <div className="mt-4 p-4 rounded-lg" style={{ background: "var(--cream)" }}>
                <p className="font-bold mb-2">Kuyash Place Restaurant</p>
                <p>Email: privacy@kuyashplace.com</p>
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
