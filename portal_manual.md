# FlexyRide: Portals Operational Manual

This manual provides a detailed overview of the various role-based portals available in the FlexyRide ecosystem. The Staff Portal uses role-based access control (RBAC) to ensure that administrators, finance teams, and support staff only see the data and controls relevant to their jobs.

---

## 🔐 Role-Based Access Control

FlexyRide categorizes staff into four distinct roles:
1. **Super Admin**: Has unrestricted access to all dashboards, settings, and system logs.
2. **Admin**: Has access to support features and broad user management.
3. **Finance**: Has access to revenue reporting and driver payout queues.
4. **Support**: Has access to driver verifications, incident resolution, and ride histories.

Upon logging in, the system automatically redirects the user to their appropriate dashboard based on their highest role.

---

## 🌍 1. Master Dashboard (`/portal/master/`)
*Access Level: Super Admin & Admin*

The Master Dashboard is the high-level command center for the entire platform.

*   **Global Users (`/master/users/`)**: Search and view every registered user (passengers and drivers). Super Admins can update roles, modify emails, toggle suspensions, and trigger manual push notifications to specific users.
*   **Platform Settings (`/master/settings/`)**: Manage dynamic configurations like Pricing Rules (base fare, distance tier multipliers) and Global Site Settings (push notification templates, surge pricing toggles).
*   **Subscriptions (`/master/subscriptions/`)**: Monitor active driver or passenger subscriptions. Includes the ability to force-cancel subscriptions that violate terms of service.
*   **Audit Logs (`/master/audit/`)**: A chronological trail of all critical actions taken by staff members. Used to track who approved a document, issued a refund, or suspended a user.
*   **Fraud Flags (`/master/audit/fraud/`)**: An automated queue of suspicious activities (e.g., GPS spoofing, velocity checks) flagged by the system for manual review.

---

## 💰 2. Finance Dashboard (`/portal/finance/`)
*Access Level: Super Admin & Finance*

The Finance Dashboard focuses strictly on money movement and platform profitability.

*   **Revenue Reports (`/finance/revenue/`)**: View aggregated data on total ride fares, platform commission earnings, and delivery fees. Filterable by date ranges.
*   **Payout Queue (`/finance/payouts/`)**: Drivers cash out their wallet balances to their mobile money or bank accounts. This queue allows finance officers to review pending withdrawal requests.
*   **Execute Payouts**: Functionality to mark a pending withdrawal as "Processed" once the funds have been disbursed via Paystack or manual bank transfer.

---

## 🛡️ 3. Support Dashboard (`/portal/support/`)
*Access Level: Super Admin, Admin, & Support*

The Support Dashboard is for day-to-day operations, dispute resolution, and customer service.

*   **Driver Verifications (`/support/verifications/`)**: The onboarding queue. Staff review uploaded documents (Driver's License, National ID, Roadworthy Certificate) and either "Approve" or "Reject" them.
*   **Ride History (`/support/rides/`)**: Searchable ledger of all rides. Essential for responding to customer complaints about specific trips.
*   **Disputes & Incidents (`/support/disputes/`)**: A ticketing system for SOS alerts, safety reports, and lost items. Staff can log notes, update the status to "Resolved", and issue partial refunds if necessary.
*   **Delivery History (`/support/deliveries/`)**: Similar to Ride History, but tailored for the courier module, including parcel details and recipient drop-off photos.

---

## 📢 4. Ads Dashboard (`/portal/ads/`)
*Access Level: Super Admin & Marketing Staff*

A specialized portal for monetizing the passenger and driver apps via in-app banner advertisements.

*   **Ad Review (`/ads/review/<uuid>/`)**: Review submitted advertisements from business partners. Staff can preview the ad creative, check the target URL, and approve or reject the campaign.
*   **Ad Configurations (`/ads/config/`)**: Control the inventory. Define how many ad slots are available per week and the pricing for standard vs. premium placements.

---

> [!TIP]
> **Best Practice**: Never share Super Admin credentials. Always provision individual accounts with the lowest necessary role (e.g., give a new customer service rep the "Support" role, not "Admin").
