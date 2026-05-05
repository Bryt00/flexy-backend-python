# FlexyRide: The Ultimate Superadmin Operational Manual

This document serves as the definitive guide for the FlexyRide Superadmin Dashboard. It provides a granular explanation of every module, model, and functional control available to platform administrators.

---

## 🏗️ 1. Core Operations (Daily Management)
These modules control the real-time movement of people and goods.

### 🚕 Rides (`rides.Ride`)
*   **Purpose**: Central log of all ride requests.
*   **Features**:
    *   **Status Tracking**: Monitor transitions from `pending` → `accepted` → `arrived` → `in_progress` → `completed`.
    *   **Route Visualization**: View pickup/dropoff coordinates and the polyline of the path taken.
    *   **Fare Audit**: See the exact breakdown of base fare, distance fee, time fee, and surge multipliers.

### 📦 Delivery Hub (`courier.Delivery`)
*   **Purpose**: Manages package delivery requests.
*   **Features**:
    *   **Parcel Details**: View weight, category (Fragile, Document, etc.), and recipient contact info.
    *   **Proof of Delivery**: Access photos uploaded by drivers upon successful drop-off.

### 🚗 Vehicle Fleet (`vehicles.Vehicle`)
*   **Purpose**: The registry of all authorized vehicles on the platform.
*   **Features**:
    *   **Type Assignment**: Assign vehicles to categories like *Go*, *Pragya*, or *Comfort*.
    *   **Document Vault**: Audit insurance and roadworthy certificates.
    *   **Verification**: Toggle the `is_verified` flag to allow a vehicle to start receiving ride requests.

### 💳 Wallets & Payments (`payments.Transaction`)
*   **Purpose**: Financial ledger for the entire platform.
*   **Features**:
    *   **Transaction Logs**: Search for specific Paystack reference IDs to troubleshoot payment failures.
    *   **Manual Adjustments**: Credit or debit user wallets for compensation or debt recovery.

---

## 📈 2. Growth & Marketing (Revenue Drivers)
Tools to scale the user base and monetize the platform.

### 📢 Ad Management (`advertising.AdBooking`)
*   **Purpose**: Manage in-app advertising slots.
*   **Features**:
    *   **Creative Review**: Preview the headline, body text, and images submitted by business partners.
    *   **Scheduling**: Approve ads for specific weeks.
    *   **Ad Slots**: Configure the maximum number of ads allowed per week and the pricing (via `AdSlotCapacity`).

### 🎫 Promos & Coupons (`marketing.PromoCode`)
*   **Purpose**: Incentivize riders with discounts.
*   **Features**:
    *   **Logic Controls**: Set percentage discounts (e.g., 20%) or flat amounts (e.g., 5 GHS).
    *   **Redemption Limits**: Restrict usage per user or total redemptions across the platform.

### 🚀 Campaigns (`marketing.Campaign`)
*   **Purpose**: Manage the visual announcements on the mobile home screen.
*   **Features**:
    *   **Banner Placement**: Upload high-resolution images for the home slider.
    *   **Deep Linking**: Set a `target_url` to send users to a specific part of the app or an external website.

---

## 🛡️ 3. Security & Support (Trust & Safety)
Maintaining the integrity and safety of the platform.

### ⚠️ Incident Hub (`rides.Incident`)
*   **Purpose**: Real-time management of SOS alerts and safety reports.
*   **Features**:
    *   **Urgency Levels**: Categorize reports as *Low*, *Medium*, or *Critical*.
    *   **Audit Log**: Document every step of the investigation and resolution process.

### 🚫 Fraud Flags (`audit.FraudFlag`)
*   **Purpose**: Proactive identification of suspicious activity.
*   **Features**:
    *   **Automated Triggers**: See flags generated for "GPS spoofing" or "Duplicate Device ID" attempts.
    *   **User Ban**: Quickly suspend a user's account if fraud is confirmed.

### 🆔 Driver Verifications (`profiles.DriverVerification`)
*   **Purpose**: The gatekeeper for driver onboarding.
*   **Features**:
    *   **Document Review**: Verify National IDs, Driving Licenses, and Background Checks.
    *   **Verification Status**: Move drivers through the `Pending` → `In Progress` → `Approved` cycle.

---

## ⚙️ 4. System & Content (Global Configuration)
Fine-tuning the platform's behavior and marketing presence.

### 🌐 Global Settings (`core_settings.SiteSetting`)
*   **Purpose**: Master switches for the entire ecosystem.
*   **Key Features**:
    *   **`maps_country_restriction`**: Comma-separated list (e.g., `gh, ng`) to lock search to specific countries.
    *   **`surge_enabled`**: Global toggle for real-time demand-based pricing.

### 💰 Pricing Rules (`core_settings.PricingRule`)
*   **Purpose**: Define how much a ride costs.
*   **Features**:
    *   **City-Specific Rates**: Set different base fares and per-km rates for Accra vs. Kumasi.
    *   **Distance Tiers**: Set higher rates for long-distance trips (via `DistanceTier`).

### 📝 Website Editor (`website.*`)
*   **Blog Posts**: Create SEO-optimized content to drive traffic.
*   **FAQ Items**: Update common questions for riders and drivers.
*   **Cities**: Update the marketing site with new regions you've launched in.
*   **Hero Banners**: Change the main background images on the marketing website.

### ☁️ File Cloud (`file_manager.FileMetadata`)
*   **Purpose**: Centralized management of all uploaded media.
*   **Features**:
    *   **Access Control**: Monitor who uploaded what file and when.
    *   **Storage Audit**: Track the total volume of driver documents and marketing assets.

---

## 📊 5. Audit & Developers
Technical logs and integration controls.

### 📜 System Audit Logs (`audit.AuditLog`)
*   **Purpose**: Accountability for admin actions.
*   **Features**:
    *   **Change History**: See exactly which admin modified a pricing rule or deleted a user.

### 🔑 API Keys (`integrations.APIKey`)
*   **Purpose**: Managing external integrations.
*   **Features**:
    *   **Secret Management**: Generate and rotate keys for third-party partners (e.g., dispatchers or aggregators).

---

> [!IMPORTANT]
> **Safety First**: Changing a **Pricing Rule** or **Global Setting** affects the entire live platform instantly. Always double-check values before saving.
