"use client";

export default function CookiePolicyPage() {
  return (
    <div className="min-h-screen pt-20 sm:pt-24 pb-12" style={{ background: "var(--gray-light)" }}>
      <div className="container-custom max-w-4xl">
        <div className="bg-white rounded-2xl p-8 sm:p-12 shadow-sm">
          <h1 className="font-black text-4xl sm:text-5xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Cookie Policy
          </h1>
          <p className="text-sm mb-8" style={{ color: "var(--text-muted)" }}>
            Last Updated: January 2025
          </p>

          <div className="space-y-8" style={{ color: "var(--black)" }}>
            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                What Are Cookies?
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                Cookies are small text files that are placed on your device when you visit our website. They help us provide you with a better experience by remembering your preferences, understanding how you use our site, and personalizing content.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                How We Use Cookies
              </h2>
              <div className="space-y-4">
                <div className="p-4 rounded-lg" style={{ background: "var(--cream)" }}>
                  <h3 className="font-bold text-lg mb-2" style={{ color: "var(--black)" }}>
                    Essential Cookies (Required)
                  </h3>
                  <p className="text-sm leading-relaxed mb-2" style={{ color: "var(--text-muted)" }}>
                    These cookies are necessary for the website to function properly. They enable core functionality such as:
                  </p>
                  <ul className="list-disc pl-6 space-y-1 text-sm" style={{ color: "var(--text-muted)" }}>
                    <li>Shopping cart management</li>
                    <li>User authentication and session management</li>
                    <li>Security and fraud prevention</li>
                    <li>Payment processing</li>
                  </ul>
                </div>

                <div className="p-4 rounded-lg" style={{ background: "#fef3c715", border: "1px solid #fef3c7" }}>
                  <h3 className="font-bold text-lg mb-2" style={{ color: "var(--black)" }}>
                    Performance Cookies (Optional)
                  </h3>
                  <p className="text-sm leading-relaxed mb-2" style={{ color: "var(--text-muted)" }}>
                    These cookies help us understand how visitors interact with our website:
                  </p>
                  <ul className="list-disc pl-6 space-y-1 text-sm" style={{ color: "var(--text-muted)" }}>
                    <li>Page visit analytics</li>
                    <li>Popular menu items tracking</li>
                    <li>Error reporting and debugging</li>
                    <li>Site performance monitoring</li>
                  </ul>
                </div>

                <div className="p-4 rounded-lg" style={{ background: "#f0f9ff", border: "1px solid #bae6fd" }}>
                  <h3 className="font-bold text-lg mb-2" style={{ color: "var(--black)" }}>
                    Functional Cookies (Optional)
                  </h3>
                  <p className="text-sm leading-relaxed mb-2" style={{ color: "var(--text-muted)" }}>
                    These cookies enable enhanced functionality and personalization:
                  </p>
                  <ul className="list-disc pl-6 space-y-1 text-sm" style={{ color: "var(--text-muted)" }}>
                    <li>Remembering your preferences (language, location)</li>
                    <li>Saved delivery addresses</li>
                    <li>Recent orders and favorites</li>
                    <li>Dietary preference settings</li>
                  </ul>
                </div>

                <div className="p-4 rounded-lg" style={{ background: "#fef2f2", border: "1px solid #fecaca" }}>
                  <h3 className="font-bold text-lg mb-2" style={{ color: "var(--black)" }}>
                    Marketing Cookies (Optional)
                  </h3>
                  <p className="text-sm leading-relaxed mb-2" style={{ color: "var(--text-muted)" }}>
                    These cookies track your online activity to deliver relevant advertisements:
                  </p>
                  <ul className="list-disc pl-6 space-y-1 text-sm" style={{ color: "var(--text-muted)" }}>
                    <li>Personalized promotions and offers</li>
                    <li>Targeted advertising on social media</li>
                    <li>Email campaign effectiveness</li>
                    <li>Cross-platform activity tracking</li>
                  </ul>
                </div>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Third-Party Cookies
              </h2>
              <div className="space-y-3 text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <p>We use third-party services that may set cookies on your device:</p>
                <ul className="list-disc pl-6 space-y-2">
                  <li><strong>Google Analytics:</strong> Website traffic and usage analysis</li>
                  <li><strong>Payment Processors:</strong> Secure transaction processing (Stripe, Paystack)</li>
                  <li><strong>Social Media:</strong> Social sharing and login features (Facebook, Google)</li>
                  <li><strong>Advertising Networks:</strong> Targeted advertising and retargeting</li>
                  <li><strong>Customer Support:</strong> Live chat and help desk functionality</li>
                </ul>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Cookie Duration
              </h2>
              <div className="space-y-3 text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <p><strong>Session Cookies:</strong> Temporary cookies that are deleted when you close your browser. Used for shopping cart and authentication.</p>
                <p><strong>Persistent Cookies:</strong> Remain on your device for a set period (typically 1-12 months). Used for preferences and analytics.</p>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Managing Your Cookie Preferences
              </h2>
              <div className="space-y-4 text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <p>You have several options to control cookies:</p>

                <div className="p-4 rounded-lg" style={{ background: "var(--cream)" }}>
                  <h3 className="font-bold mb-2" style={{ color: "var(--black)" }}>Browser Settings</h3>
                  <p className="text-sm">
                    Most browsers allow you to refuse cookies or delete existing ones through settings. However, this may limit website functionality.
                  </p>
                  <ul className="list-disc pl-6 space-y-1 text-sm mt-2">
                    <li><a href="https://support.google.com/chrome/answer/95647" target="_blank" rel="noopener noreferrer" className="underline" style={{ color: "var(--red)" }}>Chrome</a></li>
                    <li><a href="https://support.mozilla.org/en-US/kb/cookies-information-websites-store-on-your-computer" target="_blank" rel="noopener noreferrer" className="underline" style={{ color: "var(--red)" }}>Firefox</a></li>
                    <li><a href="https://support.apple.com/guide/safari/manage-cookies-sfri11471/mac" target="_blank" rel="noopener noreferrer" className="underline" style={{ color: "var(--red)" }}>Safari</a></li>
                    <li><a href="https://support.microsoft.com/en-us/microsoft-edge/delete-cookies-in-microsoft-edge" target="_blank" rel="noopener noreferrer" className="underline" style={{ color: "var(--red)" }}>Edge</a></li>
                  </ul>
                </div>

                <div className="p-4 rounded-lg" style={{ background: "var(--red)", color: "white" }}>
                  <h3 className="font-bold mb-2">Cookie Preference Center</h3>
                  <p className="text-sm mb-3">
                    You can manage your cookie preferences at any time through our Cookie Preference Center.
                  </p>
                  <button className="px-6 py-2 rounded-full font-bold transition-all hover:opacity-90" style={{ background: "white", color: "var(--red)" }}>
                    Manage Cookie Preferences
                  </button>
                </div>

                <p className="italic text-sm">
                  <strong>Note:</strong> Disabling certain cookies may affect your ability to use some features of our website, such as online ordering and account management.
                </p>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Do Not Track Signals
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                Some browsers have a "Do Not Track" feature that signals to websites that you don't want your online activity tracked. Currently, there is no industry standard for responding to these signals. We do not respond to Do Not Track signals at this time.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Mobile Devices
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                Our mobile app may use similar tracking technologies to cookies. You can manage app permissions and tracking through your device settings. Mobile advertising IDs can be reset in your phone's privacy settings.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Updates to This Policy
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                We may update this Cookie Policy from time to time to reflect changes in technology or regulations. We'll notify you of significant changes through our website or by email.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                More Information
              </h2>
              <p className="text-base leading-relaxed mb-4" style={{ color: "var(--text-muted)" }}>
                For more information about how we handle your personal data, please see our <a href="/privacy" className="underline font-bold" style={{ color: "var(--red)" }}>Privacy Policy</a>.
              </p>
              <p className="text-base leading-relaxed mb-4" style={{ color: "var(--text-muted)" }}>
                If you have questions about our use of cookies, please contact us:
              </p>
              <div className="p-4 rounded-lg" style={{ background: "var(--cream)" }}>
                <p className="font-bold mb-2">Kuyash Place Restaurant</p>
                <p>Email: privacy@kuyashplace.com</p>
                <p>Phone: +234 123 456 7890</p>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
