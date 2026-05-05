# FlexyRide Admin Portal: Operational Manual

Welcome to the FlexyRide Central Command. This manual provides a detailed guide on how to manage the FlexyRide ecosystem, from fleet operations to global system configurations.

---

## 1. Operations & Fleet Management
Managing the heartbeat of the service.

### 🚗 Vehicle Fleet
*   **Approving Vehicles**: When a driver uploads vehicle documents (Insurance, Roadworthy), they appear here. Review the files and set the status to `Approved` to allow the vehicle to go online.
*   **Vehicle Categories**: Define your fleet types (e.g., *Go*, *Pragya*, *Comfort*). Each category can have a different base fare and multiplier.

### 🛡️ Incident Hub (SOS)
*   **Emergency Response**: All SOS alerts triggered from the mobile apps appear here in real-time.
*   **Resolution**: Track the status of safety incidents and document the resolution steps taken by the support team.

### 📍 Live Map & Rides
*   **Real-time Monitoring**: View active rides on the live map.
*   **Ride History**: Audit past trips, including pickup/dropoff points, fare breakdowns, and driver/passenger details.

---

## 2. Growth & Marketing
Tools to drive user acquisition and revenue.

### 📢 Ad Management
*   **Reviewing Requests**: Advertising inquiries from the website appear here. Review the headline, body text, and target URL.
*   **Approval Workflow**: Once you approve a request, the business owner is notified via email and can proceed to payment to activate their ad in the passenger app.

### 🎫 Promos & Coupons
*   **Creating Codes**: Generate promo codes with percentage or flat-amount discounts.
*   **Usage Limits**: Set expiration dates and maximum usage counts to control your marketing budget.

### 🚀 Campaigns
*   **App Banners**: Manage the sliding banners shown on the passenger home screen. Link them to internal app pages or external URLs.

---

## 3. Financials & Wallets
Managing the flow of money.

### 💳 Transactions
*   **Audit Trail**: A centralized log of all payments (Rides, Ad Bookings, Top-ups).
*   **Status Tracking**: Monitor Paystack transaction statuses (Pending, Success, Failed).

### 👛 User Wallets
*   **Balance Management**: View and adjust user wallet balances for refunds or manual bonuses.

---

## 4. Content & System Configuration
Fine-tuning the platform behavior.

### ⚙️ Global Settings (SiteSettings)
This is the "Control Room" for the platform's behavior.
*   **`maps_country_restriction`**: Enter ISO country codes (e.g., `gh, ng`) to restrict address searching in the mobile apps. Leave blank for global search.
*   **`contact_email` / `contact_phone`**: Updates the contact details displayed on the marketing website.

### 📝 Website Editor
*   **Cities**: Add or remove cities where FlexyRide is "active." This updates the coverage map on the website.
*   **FAQ**: Manage the questions and answers shown in the app and on the web.
*   **Blog**: Publish updates, safety tips, and news to the marketing site.

### 💰 Pricing & Surge
*   **Base Fares**: Set different pricing structures for different cities.
*   **Surge Multiplier**: In high-demand periods, update the multiplier (e.g., `1.5` for 50% extra) to encourage more drivers to go online.

---

## 5. Security & Audit
Maintaining system integrity.

### 🔍 Audit Logs
*   **Action Tracking**: Every change made in this admin panel is logged here. See who changed a price, approved a driver, or modified a setting.

### 🚫 Fraud Flags
*   **Automated Alerts**: The system flags suspicious activity (e.g., multiple accounts on one device). Review these flags to suspend or ban users.

---

> [!TIP]
> **Pro-Tip**: Use the search bar at the top of the sidebar to quickly jump between sections. The interface is optimized for both desktop and tablet use.
