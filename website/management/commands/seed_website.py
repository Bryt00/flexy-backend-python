import datetime
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.utils import timezone
from website.models import BlogPost, City, Testimonial, FAQItem, JobOpening


class Command(BaseCommand):
    help = 'Seeds the database with comprehensive initial website content'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding website data...\n')

        self.seed_cities()
        self.seed_testimonials()
        self.seed_blog_posts()
        self.seed_faqs()
        self.seed_jobs()

        self.stdout.write(self.style.SUCCESS('\n[OK] Website data seeded successfully!'))

    # ─────────────────────────────────────────
    def seed_cities(self):
        cities = [
            {'name': 'Accra', 'region': 'Greater Accra', 'driver_count': 1250, 'is_active': True,
             'latitude': 5.6037, 'longitude': -0.1870,
             'cover_image_url': 'https://images.unsplash.com/photo-1598913929424-656360492160?q=80&w=800'},
            {'name': 'Kumasi', 'region': 'Ashanti', 'driver_count': 840, 'is_active': True,
             'latitude': 6.6885, 'longitude': -1.6244,
             'cover_image_url': 'https://images.unsplash.com/photo-1580674239581-4d48f7c7ef4e?q=80&w=800'},
            {'name': 'Tamale', 'region': 'Northern', 'driver_count': 320, 'is_active': True,
             'latitude': 9.4008, 'longitude': -0.8393,
             'cover_image_url': 'https://images.unsplash.com/photo-1510074377623-8cf13fb86c08?q=80&w=800'},
            {'name': 'Takoradi', 'region': 'Western', 'driver_count': 450, 'is_active': True,
             'latitude': 4.8993, 'longitude': -1.7571,
             'cover_image_url': 'https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?q=80&w=800'},
            {'name': 'Cape Coast', 'region': 'Central', 'driver_count': 210, 'is_active': True,
             'latitude': 5.1053, 'longitude': -1.2466,
             'cover_image_url': 'https://images.unsplash.com/photo-1547471080-7cc2caa01a7e?q=80&w=800'},
            {'name': 'Sunyani', 'region': 'Bono', 'driver_count': 95, 'is_active': True,
             'latitude': 7.3349, 'longitude': -2.3123,
             'cover_image_url': 'https://images.unsplash.com/photo-1570168007204-dfb528c6958f?q=80&w=800'},
            {'name': 'Ho', 'region': 'Volta', 'driver_count': 80, 'is_active': True,
             'latitude': 6.6012, 'longitude': 0.4714,
             'cover_image_url': 'https://images.unsplash.com/photo-1516026672322-bc52d61a55d5?q=80&w=800'},
            {'name': 'Bolgatanga', 'region': 'Upper East', 'driver_count': 60, 'is_active': False,
             'latitude': 10.7867, 'longitude': -0.8514,
             'cover_image_url': 'https://images.unsplash.com/photo-1509021436665-8f07dbf5bf1d?q=80&w=800'},
        ]
        created = 0
        for c in cities:
            _, was_created = City.objects.get_or_create(name=c['name'], defaults=c)
            if was_created:
                created += 1
        self.stdout.write(f'  [+] Cities: {created} created, {len(cities) - created} already existed')

    # ─────────────────────────────────────────
    def seed_testimonials(self):
        testimonials = [
            {
                'name': 'Kwame Mensah',
                'role': 'Daily Rider',
                'quote': 'FlexyRide has completely changed how I commute to work. The drivers are polite, the cars are clean, and the fares are the most competitive in Accra. I cannot imagine going back.',
                'photo_url': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=200',
                'rating': 5,
            },
            {
                'name': 'Abena Osei',
                'role': 'Business Owner',
                'quote': 'The Flexy Delivery service is a lifesaver for my boutique. Packages always arrive on time and my customers love the real-time tracking link I send them.',
                'photo_url': 'https://images.unsplash.com/photo-1531123897727-8f129e16fd3c?q=80&w=200',
                'rating': 5,
            },
            {
                'name': 'Samuel Boateng',
                'role': 'Flexy Driver',
                'quote': 'Driving with FlexyRide gives me the flexibility I need. The instant daily payouts help me manage my family finances much better than any other app I have tried.',
                'photo_url': 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?q=80&w=200',
                'rating': 5,
            },
            {
                'name': 'Ama Darkwa',
                'role': 'University Student',
                'quote': 'As a student on a budget, the affordable fares and the student promo codes make FlexyRide my go-to for getting around Kumasi safely late at night.',
                'photo_url': 'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?q=80&w=200',
                'rating': 5,
            },
            {
                'name': 'Emmanuel Tetteh',
                'role': 'Corporate Client',
                'quote': 'We moved our entire staff transport to FlexyRide Corporate. The invoicing is clean, the drivers are professional, and our account manager responds within minutes.',
                'photo_url': 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?q=80&w=200',
                'rating': 5,
            },
        ]
        created = 0
        for t in testimonials:
            _, was_created = Testimonial.objects.get_or_create(name=t['name'], defaults=t)
            if was_created:
                created += 1
        self.stdout.write(f'  [+] Testimonials: {created} created, {len(testimonials) - created} already existed')

    # ─────────────────────────────────────────
    def seed_blog_posts(self):
        now = timezone.now()
        posts = [
            {
                'title': 'Safety First: Our Commitment to Every Rider',
                'category': 'safety',
                'excerpt': 'Discover the new safety features we have implemented to ensure every FlexyRide journey is as secure as possible.',
                'content': '<h2>Your Safety is Non-Negotiable</h2><p>At FlexyRide, your safety is our top priority. We have introduced enhanced driver background checks, real-time trip sharing, and an emergency SOS button directly in the app.</p><p>These features are designed to give you peace of mind whether you are riding across Accra or delivering a parcel to a client.</p><h2>What We Have Built</h2><ul><li>Rigorous driver vetting with Ghana Police Service checks</li><li>Real-time trip sharing with family and friends</li><li>In-app SOS that alerts our 24/7 Incident Response Team</li><li>Automatic ride recording for dispute resolution</li></ul>',
                'cover_image_url': 'https://images.unsplash.com/photo-1557333610-90ee4a951ecf?q=80&w=800',
                'author_name': 'FlexyRide Safety Team',
                'is_published': True,
                'published_at': now - datetime.timedelta(days=5),
            },
            {
                'title': 'FlexyRide Is Now Live in Kumasi',
                'category': 'company',
                'excerpt': 'We are thrilled to bring the FlexyRide revolution to the heart of the Ashanti region — the Garden City.',
                'content': '<h2>Kumasi, We Are Here!</h2><p>The wait is over. FlexyRide is now officially live in Kumasi with over 840 verified drivers ready to provide safe, reliable, and affordable rides.</p><p>Download the app today and enter code <strong>KUMASI10</strong> for a discount on your first 5 rides.</p><h2>What to Expect</h2><p>Riders in Kumasi will enjoy the same premium experience our Accra users love — transparent pricing, real-time tracking, and 24/7 support.</p>',
                'cover_image_url': 'https://images.unsplash.com/photo-1580674239581-4d48f7c7ef4e?q=80&w=800',
                'author_name': 'Operations Desk',
                'is_published': True,
                'published_at': now - datetime.timedelta(days=14),
            },
            {
                'title': 'How Flexy Delivery Powers Ghana Small Businesses',
                'category': 'product',
                'excerpt': 'How our last-mile delivery service is helping local businesses scale with fast, reliable logistics.',
                'content': '<h2>Logistics Should Not Be a Bottleneck</h2><p>Flexy Delivery provides businesses of all sizes with a reliable fleet for last-mile delivery across Ghana\'s major cities.</p><p>From documents to fragile parcels, our drivers handle every delivery with care and speed. Businesses get a real-time tracking link to share with their customers.</p><h2>Success Story</h2><p>"Since switching to Flexy Delivery, our on-time delivery rate jumped from 72% to 97%." — Abena O., Boutique Owner, Accra.</p>',
                'cover_image_url': 'https://images.unsplash.com/photo-1566576721346-d4a3b4eaad55?q=80&w=800',
                'author_name': 'Product Team',
                'is_published': True,
                'published_at': now - datetime.timedelta(days=21),
            },
            {
                'title': '5 Tips to Earn More as a FlexyRide Driver',
                'category': 'driver',
                'excerpt': 'Our top-earning drivers share the habits and strategies that help them consistently maximise their weekly income.',
                'content': '<h2>Work Smarter, Not Just Harder</h2><p>We analyzed data from our top 10% of drivers and found five habits they all share:</p><ol><li><strong>Peak Hours:</strong> Log on between 6–9am and 4–8pm for surge pricing.</li><li><strong>Airport Runs:</strong> Accra and Kumasi airport rides have higher base fares.</li><li><strong>Keep a High Rating:</strong> Drivers above 4.8★ get priority in the matching algorithm.</li><li><strong>Accept Quickly:</strong> Fast acceptance rates increase your daily ride count significantly.</li><li><strong>Stay Close to Hotspots:</strong> Use the driver heatmap in the app to position yourself near demand.</li></ol>',
                'cover_image_url': 'https://images.unsplash.com/photo-1449965408869-eaa3f722e40d?q=80&w=800',
                'author_name': 'Driver Success Team',
                'is_published': True,
                'published_at': now - datetime.timedelta(days=30),
            },
            {
                'title': 'Exploring Ghana: The Best Weekend Trips from Accra',
                'category': 'travel',
                'excerpt': 'From the historic Cape Coast Castle to the lush Akosombo Dam, here are the best weekend getaways accessible from Accra.',
                'content': '<h2>Ghana Has So Much to Offer</h2><p>Accra is a fantastic base for weekend exploration. Here are our top picks:</p><ul><li><strong>Cape Coast:</strong> 3 hours by road. Visit the UNESCO-listed Cape Coast Castle and pristine beaches.</li><li><strong>Akosombo:</strong> 2 hours. The Volta River boat cruise and Akosombo Dam are unmissable.</li><li><strong>Aburi Botanical Gardens:</strong> 45 minutes. A lush escape in the Akuapem Hills.</li><li><strong>Boti Falls:</strong> 2 hours. A stunning twin waterfall hidden in Eastern Ghana.</li></ul><p>Book a FlexyRide for your next adventure and explore Ghana in comfort.</p>',
                'cover_image_url': 'https://images.unsplash.com/photo-1547471080-7cc2caa01a7e?q=80&w=800',
                'author_name': 'Travel & Lifestyle',
                'is_published': True,
                'published_at': now - datetime.timedelta(days=45),
            },
            {
                'title': 'FlexyRide Partners with Hotels for Airport Transfers',
                'category': 'company',
                'excerpt': 'We are proud to announce our new hotel partnership programme bringing seamless airport transfers to visitors across Ghana.',
                'content': '<h2>A Seamless Arrival in Ghana</h2><p>FlexyRide has partnered with leading hotels across Accra and Kumasi to provide guests with seamless, pre-booked airport transfers at guaranteed rates.</p><p>Hotel partners can now offer their guests FlexyRide vouchers at check-in, redeemable for rides anywhere in the city.</p><h2>Partner With Us</h2><p>If you operate a hotel, lodge, or guest house and would like to join our partnership programme, contact us at <a href="mailto:partnerships@flexyridegh.com">partnerships@flexyridegh.com</a>.</p>',
                'cover_image_url': 'https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?q=80&w=800',
                'author_name': 'Partnerships Team',
                'is_published': True,
                'published_at': now - datetime.timedelta(days=60),
            },
        ]
        created = 0
        for p in posts:
            slug = slugify(p['title'])[:50]
            _, was_created = BlogPost.objects.get_or_create(slug=slug, defaults={**p, 'slug': slug})
            if was_created:
                created += 1
        self.stdout.write(f'  [+] Blog Posts: {created} created, {len(posts) - created} already existed')

    # ─────────────────────────────────────────
    def seed_faqs(self):
        faqs = [
            # For Riders
            {'question': 'How do I book a ride?', 'category': 'riders', 'order': 1,
             'answer': 'Open the FlexyRide Passenger app, enter your destination, select your preferred vehicle type, and tap Book. A nearby driver will be matched to you within seconds.'},
            {'question': 'Can I schedule a ride in advance?', 'category': 'riders', 'order': 2,
             'answer': 'Yes! Tap the clock icon on the booking screen to schedule a ride up to 7 days in advance. You will receive a confirmation and a reminder 30 minutes before pickup.'},
            {'question': 'What if my driver cancels?', 'category': 'riders', 'order': 3,
             'answer': 'If a driver cancels, the app will immediately re-match you with the next available driver. There is no additional charge for driver-initiated cancellations.'},
            {'question': 'How do I share my trip with someone?', 'category': 'riders', 'order': 4,
             'answer': 'During a live trip, tap the Share button on the tracking screen and send the link to anyone. They will see your driver\'s location and your estimated arrival time in real-time.'},
            {'question': 'What is the cancellation policy for riders?', 'category': 'riders', 'order': 5,
             'answer': 'You can cancel for free within 2 minutes of booking. After 2 minutes, a small cancellation fee may apply if the driver is already on their way to you.'},

            # For Drivers
            {'question': 'How do I sign up to drive with FlexyRide?', 'category': 'drivers', 'order': 1,
             'answer': 'Download the FlexyRide Driver app, tap Sign Up, and complete the registration. You will need a valid Ghana driving licence, a roadworthy vehicle, and pass our background check.'},
            {'question': 'How quickly can I start earning?', 'category': 'drivers', 'order': 2,
             'answer': 'Once your documents are verified and approved (typically 1–3 business days), you can start accepting rides immediately.'},
            {'question': 'When and how do I get paid?', 'category': 'drivers', 'order': 3,
             'answer': 'Drivers receive daily payouts to their Mobile Money account. Earnings from trips completed by midnight are typically deposited the following morning.'},
            {'question': 'What percentage does FlexyRide take?', 'category': 'drivers', 'order': 4,
             'answer': 'FlexyRide charges a 15% platform fee. You keep 85% of every fare — one of the best driver splits in Ghana.'},
            {'question': 'Can I drive my own vehicle?', 'category': 'drivers', 'order': 5,
             'answer': 'Yes. You must use your own vehicle, which must pass our inspection for roadworthiness and cleanliness standards. Vehicle requirements vary by ride category.'},

            # Payments
            {'question': 'What payment methods are accepted?', 'category': 'payments', 'order': 1,
             'answer': 'We accept Mobile Money (MTN MoMo, Vodafone Cash, AirtelTigo Money), debit/credit cards, and FlexyRide Wallet balance.'},
            {'question': 'Can I pay with cash?', 'category': 'payments', 'order': 2,
             'answer': 'Cash payments are currently not supported. All rides must be paid digitally through the app to ensure secure, transparent transactions.'},
            {'question': 'How do I add money to my FlexyRide Wallet?', 'category': 'payments', 'order': 3,
             'answer': 'Go to Wallet in the app, tap Top Up, enter an amount, and select your Mobile Money number or card. Funds are added instantly.'},
            {'question': 'What happens if I am overcharged?', 'category': 'payments', 'order': 4,
             'answer': 'Every fare is calculated by the app based on distance and time — drivers cannot change the price. If you believe there is an error, contact support within 24 hours with your trip ID.'},

            # Safety
            {'question': 'How are drivers vetted?', 'category': 'safety', 'order': 1,
             'answer': 'Every driver undergoes a Ghana Police Service criminal background check, driving licence verification, and a vehicle roadworthiness inspection before being approved.'},
            {'question': 'What should I do in an emergency during a ride?', 'category': 'safety', 'order': 2,
             'answer': 'Tap the SOS button (shield icon) on the live trip screen. This will immediately alert our 24/7 Incident Response Team and share your GPS location with them.'},
            {'question': 'Can I verify my driver before getting in?', 'category': 'safety', 'order': 3,
             'answer': 'Yes. Before entering any vehicle, check that the car plate, driver photo, and name in the app match the vehicle and driver in front of you.'},

            # General
            {'question': 'Which cities does FlexyRide operate in?', 'category': 'general', 'order': 1,
             'answer': 'FlexyRide currently operates in Accra, Kumasi, Tamale, Takoradi, Cape Coast, and Sunyani, with more cities being added throughout 2025.'},
            {'question': 'How do I contact customer support?', 'category': 'general', 'order': 2,
             'answer': 'You can reach our support team 24/7 via the in-app chat, email at support@flexyridegh.com, or through our Contact Us page on this website.'},
            {'question': 'Is there a FlexyRide for iOS?', 'category': 'general', 'order': 3,
             'answer': 'The Android app is available now on Google Play. Our iOS app is currently in final testing and will be available on the App Store very soon.'},
        ]
        created = 0
        for f in faqs:
            _, was_created = FAQItem.objects.get_or_create(question=f['question'], defaults=f)
            if was_created:
                created += 1
        self.stdout.write(f'  [+] FAQ Items: {created} created, {len(faqs) - created} already existed')

    # ─────────────────────────────────────────
    def seed_jobs(self):
        jobs = [
            {
                'title': 'Senior Backend Engineer (Python/Django)',
                'department': 'engineering',
                'location': 'Accra, Ghana (Hybrid)',
                'job_type': 'full_time',
                'description': 'We are looking for a Senior Backend Engineer to help scale our ride-hailing platform to millions of users. You will own core services including ride matching, pricing, and payments.',
                'requirements': '5+ years Python experience. Strong knowledge of Django REST Framework. Experience with PostgreSQL, Redis, and Celery. Familiarity with real-time systems (WebSockets, channels) is a plus.',
            },
            {
                'title': 'Flutter Mobile Engineer',
                'department': 'engineering',
                'location': 'Accra, Ghana (Hybrid)',
                'job_type': 'full_time',
                'description': 'Build and maintain our Passenger and Driver apps used by hundreds of thousands of Ghanaians daily. You will work closely with our design and backend teams to ship impactful features.',
                'requirements': '3+ years Flutter/Dart experience. Solid understanding of state management (BLoC preferred). Experience with Google Maps SDK and real-time location features.',
            },
            {
                'title': 'City Operations Manager – Kumasi',
                'department': 'operations',
                'location': 'Kumasi, Ghana',
                'job_type': 'full_time',
                'description': 'Lead all on-the-ground operations in Kumasi. You will be responsible for driver acquisition, retention, quality assurance, and local partnerships.',
                'requirements': '3+ years in operations or logistics management. Strong network in the Kumasi business community. Excellent communication and problem-solving skills.',
            },
            {
                'title': 'Growth Marketing Manager',
                'department': 'marketing',
                'location': 'Accra, Ghana',
                'job_type': 'full_time',
                'description': 'Own rider and driver acquisition campaigns across digital and traditional channels. Drive down CAC while increasing LTV through creative, data-driven campaigns.',
                'requirements': '4+ years growth or performance marketing experience. Proven track record with Meta Ads and Google Ads. Experience in a two-sided marketplace is strongly preferred.',
            },
            {
                'title': 'Customer Support Lead',
                'department': 'support',
                'location': 'Accra, Ghana',
                'job_type': 'full_time',
                'description': 'Build and manage our customer support team to deliver world-class service to riders and drivers 24/7. You will define support processes, SLAs, and quality standards.',
                'requirements': '3+ years in customer support leadership. Experience with support tooling (Freshdesk, Zendesk, or similar). Empathetic communicator with strong analytical skills.',
            },
            {
                'title': 'UI/UX Designer',
                'department': 'design',
                'location': 'Accra, Ghana (Remote-Friendly)',
                'job_type': 'full_time',
                'description': 'Design beautiful, intuitive experiences for our Passenger app, Driver app, and website. You will run user research, create wireframes, and collaborate with engineering to bring designs to life.',
                'requirements': '3+ years UI/UX design experience. Expert in Figma. Portfolio demonstrating strong visual design and user-centered thinking. Mobile app design experience is required.',
            },
            {
                'title': 'Finance & Compliance Intern',
                'department': 'finance',
                'location': 'Accra, Ghana',
                'job_type': 'internship',
                'description': 'Support our finance team with reconciliations, driver payout reports, and compliance documentation. A great opportunity to gain hands-on fintech experience.',
                'requirements': 'Pursuing or completed a degree in Finance, Accounting, or Economics. Proficient in Excel. Detail-oriented with strong numerical skills.',
            },
            {
                'title': 'Independent Commission-Based Sales Partners & Freelance Marketers',
                'department': 'marketing',
                'location': 'Nationwide, Ghana (Remote)',
                'job_type': 'contract',
                'description': """
<h3>Trading in Ghana as PatMacTech Solutions</h3>
<p>Are you confident, persuasive, business-minded, and hungry to earn based on performance? <strong>PatMacTech UK Ltd</strong> is expanding across Ghana and we are recruiting ambitious individuals in Accra, Kumasi, and nationwide to help market our growing portfolio of digital platforms, business services, and technology solutions.</p>

<h4>This opportunity is ideal for:</h4>
<ul>
    <li>Freelancers & Students</li>
    <li>National Service Personnel</li>
    <li>Sales & Digital Marketers</li>
    <li>Side-hustle professionals & Social media influencers</li>
    <li>Anyone confident in communication and business development</li>
</ul>

<h3>ABOUT THE ROLE</h3>
<p>You will work as an <strong>Independent Commission-Based Sales Partner</strong> representing PatMacTech Solutions in Ghana. You will help promote and secure customers for:</p>
<ul>
    <li><strong>PMTHRFlow</strong> – HR & workforce management platform</li>
    <li><strong>FlexyRide Ghana</strong> – Ride-hailing & mobility platform</li>
    <li><strong>PatMacTech</strong> business and IT services</li>
</ul>

<h3>WHAT YOU WILL DO</h3>
<h4>Online Marketers</h4>
<ul>
    <li>Promote products on social media and generate leads online.</li>
    <li>Engage businesses digitally via WhatsApp, TikTok, Facebook, Instagram, and LinkedIn.</li>
    <li>Follow up with potential clients and book demos/consultations.</li>
</ul>

<h4>Field / Walk-About Marketers</h4>
<ul>
    <li>Visit businesses physically to introduce company services.</li>
    <li>Register interested customers and build relationships with SMEs, organizations, and businesses.</li>
    <li>Represent the company professionally in public.</li>
</ul>

<h3>EARNINGS & COMMISSION</h3>
<p>This is a <strong>pure commission-based opportunity</strong> with strong earning potential. Successful marketers will receive:</p>
<ul>
    <li><strong>10% Commission</strong> on subscription services, one-off sales, and business service contracts.</li>
    <li><strong>Commission Duration:</strong> You will continue earning commission on qualifying subscription payments for up to <strong>6 months</strong> per client you onboard.</li>
    <li>There is <strong>NO earning cap</strong>.</li>
</ul>

<h3>WHAT WE PROVIDE</h3>
<ul>
    <li>Official company onboarding and product training.</li>
    <li>Marketing support materials and company communication system access.</li>
    <li>Remote working flexibility and future leadership opportunities for top performers.</li>
</ul>

<h3>REQUIREMENTS</h3>
<ul>
    <li>Confident communication and self-motivation.</li>
    <li>Access to a smartphone or laptop and personal headphones/earpieces.</li>
    <li>Willingness to learn company products and be professional and reliable.</li>
</ul>

<h3>HOW TO APPLY</h3>
<p>Send your <strong>Full Name, Location, Phone Number, and Brief Background</strong> to:</p>
<ul>
    <li>📧 <strong>Email:</strong> admin@patmactechuk.net</li>
    <li>📱 <strong>WhatsApp:</strong> +447413025596</li>
    <li><strong>Subject:</strong> Application – Independent Sales Partner Ghana</li>
</ul>
                """,
                'requirements': 'Confident communication, self-motivated, access to smartphone/laptop, and professional reliability.',
            },
        ]
        created = 0
        for j in jobs:
            _, was_created = JobOpening.objects.update_or_create(title=j['title'], defaults=j)
            if was_created:
                created += 1
        self.stdout.write(f'  [+] Job Openings: {created} created, {len(jobs) - created} updated')
