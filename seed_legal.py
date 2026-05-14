import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from website.models import LegalDocument

TERMS_CONTENT = """
<h2>1. Acceptance of Terms</h2>
<p>By accessing or using the FlexyRide platform, including our mobile applications and website (collectively, the "Service"), you agree to be bound by these Terms of Service. If you do not agree to these terms, you may not use the Service.</p>

<h2>2. Description of Service</h2>
<p>FlexyRide is a technology platform that connects passengers with independent drivers for on-demand transportation services. FlexyRide does not provide transportation services directly and is not a transportation carrier.</p>

<h2>3. User Accounts</h2>
<p>To use the Service, you must register for an account. You agree to:</p>
<ul>
  <li>Provide accurate, current, and complete information during registration</li>
  <li>Maintain the security of your password and account</li>
  <li>Accept responsibility for all activities that occur under your account</li>
  <li>Notify FlexyRide immediately of any unauthorized use of your account</li>
</ul>
<p>You must be at least 18 years of age to create an account and use the Service.</p>

<h2>4. Rides and Payments</h2>
<p>When you request a ride through the Service, you agree to pay the fare displayed at the time of booking. Fares are calculated based on distance, time, vehicle type, and applicable surge pricing. All payments are processed securely through our integrated payment partners.</p>
<ul>
  <li>Fares are estimated before the ride and finalized upon completion</li>
  <li>Cancellation fees may apply if you cancel a ride after a driver has been dispatched</li>
  <li>Tips are optional and go directly to your driver</li>
  <li>Promotional credits and discounts are subject to their specific terms</li>
</ul>

<h2>5. User Conduct</h2>
<p>You agree not to:</p>
<ul>
  <li>Use the Service for any unlawful purpose or in violation of any applicable laws</li>
  <li>Harass, threaten, or harm drivers, other passengers, or FlexyRide staff</li>
  <li>Damage or soil a driver's vehicle</li>
  <li>Transport illegal substances or hazardous materials</li>
  <li>Allow unauthorized third parties to use your account</li>
  <li>Attempt to manipulate fares, ratings, or promotional offers</li>
</ul>

<h2>6. Driver Requirements</h2>
<p>Drivers on the FlexyRide platform must:</p>
<ul>
  <li>Hold a valid driver's license and vehicle registration</li>
  <li>Maintain adequate vehicle insurance as required by local law</li>
  <li>Pass background and vehicle verification checks</li>
  <li>Maintain their vehicle in safe operating condition</li>
  <li>Comply with all applicable traffic laws and regulations</li>
</ul>

<h2>7. Limitation of Liability</h2>
<p>FlexyRide provides the platform on an "as is" basis. To the maximum extent permitted by law, FlexyRide shall not be liable for any indirect, incidental, special, consequential, or punitive damages, including but not limited to loss of profits, data, or goodwill, arising out of or in connection with your use of the Service.</p>

<h2>8. Intellectual Property</h2>
<p>The FlexyRide name, logo, and all related trademarks, service marks, and trade names are the property of FlexyRide. You may not use, copy, or distribute any FlexyRide intellectual property without prior written consent.</p>

<h2>9. Termination</h2>
<p>FlexyRide reserves the right to suspend or terminate your account at any time, with or without cause, including but not limited to violations of these Terms of Service. Upon termination, your right to use the Service will immediately cease.</p>

<h2>10. Governing Law</h2>
<p>These Terms shall be governed by and construed in accordance with the laws of the Republic of Ghana. Any disputes arising from or relating to these Terms shall be subject to the exclusive jurisdiction of the courts of Ghana.</p>

<h2>11. Changes to Terms</h2>
<p>FlexyRide reserves the right to modify these Terms at any time. We will notify you of significant changes through the app or via email. Your continued use of the Service after such changes constitutes acceptance of the updated Terms.</p>

<h2>12. Contact Us</h2>
<p>If you have any questions about these Terms of Service, please contact us at <strong>support@flexyride.com</strong>.</p>
"""

PRIVACY_CONTENT = """
<h2>1. Introduction</h2>
<p>FlexyRide ("we", "our", or "us") is committed to protecting the privacy of our users. This Privacy Policy explains how we collect, use, disclose, and safeguard your personal information when you use our mobile applications, website, and related services (collectively, the "Service").</p>

<h2>2. Information We Collect</h2>
<h3>Personal Information</h3>
<p>When you create an account or use the Service, we may collect:</p>
<ul>
  <li>Full name, email address, and phone number</li>
  <li>Profile photo and date of birth</li>
  <li>Payment information (processed securely through our payment partners)</li>
  <li>Driver's license, vehicle registration, and insurance documents (for drivers)</li>
</ul>

<h3>Location Data</h3>
<p>We collect precise location data from your device to:</p>
<ul>
  <li>Connect you with nearby drivers</li>
  <li>Calculate fares and provide route navigation</li>
  <li>Provide real-time ride tracking and ETAs</li>
  <li>Improve our services and detect fraud</li>
</ul>

<h3>Usage Data</h3>
<p>We automatically collect information about your interactions with the Service, including:</p>
<ul>
  <li>Ride history, including pickup and drop-off locations</li>
  <li>App usage patterns and preferences</li>
  <li>Device information (model, operating system, unique identifiers)</li>
  <li>Log data (IP address, access times, pages viewed)</li>
</ul>

<h2>3. How We Use Your Information</h2>
<p>We use the information we collect to:</p>
<ul>
  <li>Provide, maintain, and improve the Service</li>
  <li>Process transactions and send related notifications</li>
  <li>Connect passengers with drivers and facilitate rides</li>
  <li>Ensure safety and security for all users</li>
  <li>Personalize your experience and provide customer support</li>
  <li>Comply with legal obligations and enforce our terms</li>
  <li>Send promotional communications (with your consent)</li>
</ul>

<h2>4. Information Sharing</h2>
<p>We may share your information with:</p>
<ul>
  <li><strong>Drivers/Passengers:</strong> Limited information necessary to facilitate your ride (name, pickup location, ratings)</li>
  <li><strong>Payment Processors:</strong> To process your transactions securely</li>
  <li><strong>Service Providers:</strong> Third parties who assist in operating the Service (cloud hosting, analytics, customer support)</li>
  <li><strong>Law Enforcement:</strong> When required by law or to protect the rights, safety, or property of FlexyRide, our users, or others</li>
</ul>
<p>We do not sell your personal information to third parties.</p>

<h2>5. Data Security</h2>
<p>We implement industry-standard security measures to protect your personal information, including:</p>
<ul>
  <li>Encryption of data in transit and at rest</li>
  <li>Secure authentication and access controls</li>
  <li>Regular security audits and vulnerability assessments</li>
  <li>Employee training on data protection best practices</li>
</ul>
<p>However, no method of transmission over the internet or electronic storage is 100% secure. We cannot guarantee absolute security of your data.</p>

<h2>6. Data Retention</h2>
<p>We retain your personal information for as long as your account is active or as needed to provide the Service. We may also retain certain information as required by law, for legitimate business purposes, or to resolve disputes.</p>

<h2>7. Your Rights</h2>
<p>You have the right to:</p>
<ul>
  <li>Access and receive a copy of your personal data</li>
  <li>Correct inaccurate or incomplete information</li>
  <li>Request deletion of your account and personal data</li>
  <li>Opt out of promotional communications</li>
  <li>Disable location services (though this may limit Service functionality)</li>
</ul>
<p>To exercise these rights, contact us at <strong>privacy@flexyride.com</strong> or use the account settings in the app.</p>

<h2>8. Children's Privacy</h2>
<p>The Service is not intended for users under the age of 18. We do not knowingly collect personal information from children. If you believe a child has provided us with personal information, please contact us immediately.</p>

<h2>9. Changes to This Policy</h2>
<p>We may update this Privacy Policy from time to time. We will notify you of material changes through the app or by email. Your continued use of the Service after changes take effect constitutes acceptance of the updated policy.</p>

<h2>10. Contact Us</h2>
<p>If you have any questions or concerns about this Privacy Policy or our data practices, please contact us:</p>
<ul>
  <li><strong>Email:</strong> privacy@flexyride.com</li>
  <li><strong>Support:</strong> support@flexyride.com</li>
  <li><strong>Address:</strong> FlexyRide Technologies, Accra, Ghana</li>
</ul>
"""


def seed():
    # Terms of Service
    terms, created = LegalDocument.objects.update_or_create(
        document_type='terms',
        defaults={
            'title': 'Terms of Service',
            'slug': 'terms-of-service',
            'content': TERMS_CONTENT.strip(),
        }
    )
    print(f"{'Created' if created else 'Updated'} Terms of Service")

    # Privacy Policy
    privacy, created = LegalDocument.objects.update_or_create(
        document_type='privacy',
        defaults={
            'title': 'Privacy Policy',
            'slug': 'privacy-policy',
            'content': PRIVACY_CONTENT.strip(),
        }
    )
    print(f"{'Created' if created else 'Updated'} Privacy Policy")

    print("\nLegal documents seeded successfully!")


if __name__ == '__main__':
    seed()
