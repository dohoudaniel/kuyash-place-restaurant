"use client";

export default function AccessibilityPage() {
  return (
    <div className="min-h-screen pt-20 sm:pt-24 pb-12" style={{ background: "var(--gray-light)" }}>
      <div className="container-custom max-w-4xl">
        <div className="bg-white rounded-2xl p-8 sm:p-12 shadow-sm">
          <h1 className="font-black text-4xl sm:text-5xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Accessibility Statement
          </h1>
          <p className="text-sm mb-8" style={{ color: "var(--text-muted)" }}>
            Last Updated: January 2025
          </p>

          <div className="space-y-8" style={{ color: "var(--black)" }}>
            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Our Commitment
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                Kuyash Place Restaurant is committed to ensuring digital accessibility for people with disabilities. We are continually improving the user experience for everyone and applying relevant accessibility standards to ensure our website and services are accessible to all.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Accessibility Standards
              </h2>
              <p className="text-base leading-relaxed mb-4" style={{ color: "var(--text-muted)" }}>
                We strive to conform to the Web Content Accessibility Guidelines (WCAG) 2.1 Level AA standards. These guidelines explain how to make web content more accessible for people with disabilities and user-friendly for everyone.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Website Accessibility Features
              </h2>
              <div className="space-y-4">
                <div className="p-4 rounded-lg" style={{ background: "var(--cream)" }}>
                  <h3 className="font-bold text-lg mb-2" style={{ color: "var(--black)" }}>
                    Navigation & Structure
                  </h3>
                  <ul className="list-disc pl-6 space-y-2 text-sm" style={{ color: "var(--text-muted)" }}>
                    <li>Clear and consistent navigation throughout the site</li>
                    <li>Proper heading hierarchy for screen readers</li>
                    <li>Skip navigation links to bypass repetitive content</li>
                    <li>Logical tab order for keyboard navigation</li>
                    <li>Breadcrumb navigation on complex pages</li>
                  </ul>
                </div>

                <div className="p-4 rounded-lg" style={{ background: "#f0f9ff", border: "1px solid #bae6fd" }}>
                  <h3 className="font-bold text-lg mb-2" style={{ color: "var(--black)" }}>
                    Visual Design
                  </h3>
                  <ul className="list-disc pl-6 space-y-2 text-sm" style={{ color: "var(--text-muted)" }}>
                    <li>High contrast text and backgrounds (WCAG AA compliant)</li>
                    <li>Resizable text up to 200% without loss of functionality</li>
                    <li>Clear focus indicators for interactive elements</li>
                    <li>Information conveyed through multiple visual cues, not just color</li>
                    <li>Responsive design for various screen sizes</li>
                  </ul>
                </div>

                <div className="p-4 rounded-lg" style={{ background: "#fef3c715", border: "1px solid #fef3c7" }}>
                  <h3 className="font-bold text-lg mb-2" style={{ color: "var(--black)" }}>
                    Content & Media
                  </h3>
                  <ul className="list-disc pl-6 space-y-2 text-sm" style={{ color: "var(--text-muted)" }}>
                    <li>Alternative text for all images and graphics</li>
                    <li>Captions and transcripts for video content</li>
                    <li>Clear and simple language throughout</li>
                    <li>Descriptive link text (avoiding "click here")</li>
                    <li>Properly labeled form fields and inputs</li>
                  </ul>
                </div>

                <div className="p-4 rounded-lg" style={{ background: "#fef2f2", border: "1px solid #fecaca" }}>
                  <h3 className="font-bold text-lg mb-2" style={{ color: "var(--black)" }}>
                    Interactive Features
                  </h3>
                  <ul className="list-disc pl-6 space-y-2 text-sm" style={{ color: "var(--text-muted)" }}>
                    <li>Keyboard accessible for all functionality</li>
                    <li>ARIA labels for dynamic content and interactions</li>
                    <li>Error messages clearly identified and described</li>
                    <li>Sufficient time to complete forms and checkout</li>
                    <li>Pause/stop options for auto-updating content</li>
                  </ul>
                </div>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Restaurant Accessibility
              </h2>
              <div className="space-y-3 text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <p>Our physical restaurant locations are designed to be welcoming and accessible:</p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>Wheelchair accessible entrances and ramps</li>
                  <li>Accessible parking spaces near entrances</li>
                  <li>Wide aisles and table spacing for mobility devices</li>
                  <li>Accessible restrooms with grab bars and wider stalls</li>
                  <li>Braille and large-print menus available upon request</li>
                  <li>Staff trained in assisting guests with disabilities</li>
                  <li>Service animals welcome</li>
                  <li>Hearing loop system for customers with hearing aids</li>
                </ul>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Dietary Accommodations
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                We accommodate various dietary needs and restrictions. Our menu clearly indicates allergens, and our staff can provide detailed ingredient information. Please inform us of any allergies or dietary requirements when ordering.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Assistive Technology Compatibility
              </h2>
              <div className="space-y-3 text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <p>Our website has been tested with the following assistive technologies:</p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>Screen readers (JAWS, NVDA, VoiceOver)</li>
                  <li>Screen magnification software (ZoomText, MAGic)</li>
                  <li>Speech recognition software (Dragon NaturallySpeaking)</li>
                  <li>Browser zoom functions (up to 200%)</li>
                  <li>Keyboard-only navigation</li>
                </ul>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Third-Party Content
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                Some content on our website may be provided by third-party services (maps, payment processors, social media). We work with partners who share our commitment to accessibility, but we may have limited control over their accessibility features.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Known Limitations
              </h2>
              <p className="text-base leading-relaxed mb-3" style={{ color: "var(--text-muted)" }}>
                Despite our best efforts, some limitations may exist:
              </p>
              <ul className="list-disc pl-6 space-y-2 text-base" style={{ color: "var(--text-muted)" }}>
                <li>Some older PDF documents may not be fully accessible</li>
                <li>User-generated content (reviews) may not meet accessibility standards</li>
                <li>Some third-party embedded content may have accessibility barriers</li>
              </ul>
              <p className="text-base leading-relaxed mt-3" style={{ color: "var(--text-muted)" }}>
                We are actively working to address these limitations in future updates.
              </p>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Ongoing Improvements
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                Accessibility is an ongoing effort. We regularly:
              </p>
              <ul className="list-disc pl-6 space-y-2 text-base mt-3" style={{ color: "var(--text-muted)" }}>
                <li>Conduct accessibility audits and testing</li>
                <li>Train our development team on accessibility best practices</li>
                <li>Incorporate user feedback to improve accessibility</li>
                <li>Update our website to meet evolving standards</li>
                <li>Monitor and fix accessibility issues as they arise</li>
              </ul>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Alternative Ordering Methods
              </h2>
              <p className="text-base leading-relaxed mb-3" style={{ color: "var(--text-muted)" }}>
                If you experience difficulty using our website, we offer alternative ways to order:
              </p>
              <div className="p-4 rounded-lg" style={{ background: "var(--cream)" }}>
                <ul className="space-y-2 text-base">
                  <li><strong>Phone:</strong> Call +234 123 456 7890 to place an order with our staff</li>
                  <li><strong>Email:</strong> Send your order to orders@kuyashplace.com</li>
                  <li><strong>In-Person:</strong> Visit any of our locations to order directly</li>
                  <li><strong>WhatsApp:</strong> Message us at +234 123 456 7890</li>
                </ul>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Feedback & Support
              </h2>
              <p className="text-base leading-relaxed mb-4" style={{ color: "var(--text-muted)" }}>
                We welcome your feedback on the accessibility of our website and services. If you encounter an accessibility barrier or have suggestions for improvement, please let us know:
              </p>
              <div className="p-6 rounded-xl" style={{ background: "var(--red)", color: "white" }}>
                <h3 className="font-bold text-xl mb-3">Accessibility Feedback</h3>
                <p className="mb-3">Email: accessibility@kuyashplace.com</p>
                <p className="mb-3">Phone: +234 123 456 7890</p>
                <p className="mb-4">We aim to respond to accessibility feedback within 3 business days.</p>
                <button className="px-6 py-3 rounded-full font-bold transition-all hover:opacity-90" style={{ background: "white", color: "var(--red)" }}>
                  Report Accessibility Issue
                </button>
              </div>
            </section>

            <section>
              <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                Formal Complaints
              </h2>
              <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
                If you are not satisfied with our response to your accessibility concerns, you may escalate the issue to our Customer Service Manager at customerservice@kuyashplace.com or contact the relevant regulatory authority in your jurisdiction.
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
