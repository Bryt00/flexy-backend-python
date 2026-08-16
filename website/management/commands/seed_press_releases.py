from django.core.management.base import BaseCommand
from django.utils import timezone
import datetime
from website.models import PressRelease, PressDownload

class Command(BaseCommand):
    help = 'Seeds initial Press Release listings matching the design mockups.'

    def handle(self, *args, **options):
        self.stdout.write("Seeding Press Releases...")

        releases_data = [
            {
                'title': 'FlexyRide Launches Global Initiative to Empower Communities',
                'slug': 'flexyride-launches-global-initiative-to-empower-communities',
                'subtitle': 'New initiative aims to advance education, sustainability, and economic mobility in underserved urban communities nationwide.',
                'category': 'initiatives',
                'location': 'Accra, Ghana',
                'published_at': timezone.now() - datetime.timedelta(days=2),
                'cover_image_url': 'https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=800&auto=format&fit=crop&q=80',
                'content': '''
                <p><strong>FlexyRide</strong>, Ghana's premier ride-hailing and urban logistics platform, today announced the launch of its landmark community empowerment program, <em>FlexyImpact 2030</em>.</p>
                <p>This initiative focuses on three key pillars: <strong>Driver Welfare & Education, Clean Mobility & Carbon Neutrality, and Economic Inclusion</strong>. Through strategic local partnerships, FlexyRide aims to support over 50,000 drivers and small vendors across West Africa by 2030.</p>
                <blockquote>"At FlexyRide, we believe mobility is the heartbeat of opportunity," said Dr. Kwesi Mensah, CEO of FlexyRide. "FlexyImpact 2030 is our commitment to transforming urban transportation into a catalyst for social and economic empowerment."</blockquote>
                <p>The initiative will roll out in phases across Accra, Kumasi, Takoradi, and Tamale, featuring driver health micro-insurance, electric vehicle adoption incentives, and youth tech scholarships.</p>
                '''
            },
            {
                'title': 'FlexyRide Partners with Global Leaders to Tackle Urban Hunger',
                'slug': 'flexyride-partners-with-global-leaders-to-tackle-hunger',
                'subtitle': 'Partnership will support food security programs and leverage FlexyRide logistics to deliver essential meals to vulnerable families.',
                'category': 'partnerships',
                'location': 'Kumasi, Ghana',
                'published_at': timezone.now() - datetime.timedelta(days=15),
                'cover_image_url': 'https://images.unsplash.com/photo-1488521787991-ed7bbaae773c?w=800&auto=format&fit=crop&q=80',
                'content': '''
                <p>FlexyRide has joined forces with international humanitarian organization FoodForLife to expand food delivery capabilities across regional capitals in Ghana.</p>
                <p>By leveraging FlexyRide Courier networks, over 100,000 hot meals and dry food packages will be dispatched directly to community centers and shelter homes.</p>
                <blockquote>"Using our fleet for good ensures no surplus food goes to waste when families are in need," stated Abena Osei, Head of Impact at FlexyRide.</blockquote>
                '''
            },
            {
                'title': 'FlexyRide Hosts International Urban Mobility & Tech Summit',
                'slug': 'flexyride-hosts-international-mobility-tech-summit',
                'subtitle': 'Leaders and tech innovators from around the world gathered in Accra to inspire action and drive sustainable smart city development.',
                'category': 'events',
                'location': 'Accra, Ghana',
                'published_at': timezone.now() - datetime.timedelta(days=40),
                'cover_image_url': 'https://images.unsplash.com/photo-1511578314322-379afb476865?w=800&auto=format&fit=crop&q=80',
                'content': '''
                <p>Over 500 transport policymakers, technology leaders, and urban planners converged for the inaugural <strong>FlexyRide Mobility Summit 2026</strong> at the Accra International Conference Centre.</p>
                <p>Key topics included AI-driven dispatch optimization, EV charging infrastructure readiness, and digital payment integrations for public transport operators.</p>
                '''
            },
            {
                'title': 'FlexyRide Reaches Milestone of 500,000 Safe Completed Trips',
                'slug': 'flexyride-reaches-milestone-500k-safe-trips',
                'subtitle': 'Celebrating the completion of half a million trips with an industry-leading 99.9% safety rating across Ghana.',
                'category': 'impact',
                'location': 'Takoradi, Ghana',
                'published_at': timezone.now() - datetime.timedelta(days=70),
                'cover_image_url': 'https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=800&auto=format&fit=crop&q=80',
                'content': '''
                <p>FlexyRide officially hit the milestone of 500,000 completed passenger and delivery trips today.</p>
                <p>The achievement reflects the platform's unwavering focus on real-time GPS tracking, dual SOS safety triggers, and thorough driver background checks.</p>
                '''
            },
            {
                'title': 'FlexyRide Releases 2025 Annual Impact and Sustainability Report',
                'slug': 'flexyride-releases-2025-annual-impact-report',
                'subtitle': 'Our annual report highlights key achievements, driver earnings growth, financial stewardship, and community impact.',
                'category': 'reports',
                'location': 'Accra, Ghana',
                'published_at': timezone.now() - datetime.timedelta(days=95),
                'cover_image_url': 'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=800&auto=format&fit=crop&q=80',
                'content': '''
                <p>FlexyRide has published its <em>2025 Impact & Sustainability Report</em>, detailing a 40% year-over-year increase in driver take-home earnings and zero safety incident defaults.</p>
                '''
            },
            {
                'title': 'FlexyRide Appoints New Advisory Board Members to Drive Regional Vision',
                'slug': 'flexyride-appoints-new-advisory-board-members',
                'subtitle': 'New strategic leadership additions bring diverse expertise to strengthen corporate governance and accelerate expansion.',
                'category': 'announcements',
                'location': 'Accra, Ghana',
                'published_at': timezone.now() - datetime.timedelta(days=120),
                'cover_image_url': 'https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=800&auto=format&fit=crop&q=80',
                'content': '''
                <p>FlexyRide is proud to welcome three distinguished leaders to its Board of Directors to guide the company's next phase of West African expansion.</p>
                '''
            }
        ]

        count = 0
        for item in releases_data:
            release, created = PressRelease.objects.update_or_create(
                slug=item['slug'],
                defaults=item
            )
            if created:
                count += 1

        # Seed Sample Downloads
        PressDownload.objects.get_or_create(
            title='FlexyRide Impact 2026 Overview (PDF)',
            defaults={'file_type': 'PDF', 'external_url': '#', 'is_active': True}
        )
        PressDownload.objects.get_or_create(
            title='Official FlexyRide Media Kit (ZIP)',
            defaults={'file_type': 'ZIP', 'external_url': '#', 'is_active': True}
        )

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {count} new Press Releases and downloads."))
