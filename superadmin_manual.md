# FlexyRide: The Ultimate Superadmin Operational Manual

This document serves as the definitive guide for the FlexyRide Superadmin Dashboard. It provides a clear explanation of every section and functional control available to platform administrators.

---

## 1. Core Operations (Daily Management)
These sections control the real-time movement of people and goods.

### 🚕 Rides
*   **Purpose**: Central log of all ride requests.
*   **Features**:
    *   **Status Tracking**: Monitor transitions from `pending` → `accepted` → `arrived` → `in progress` → `completed`.
    *   **Route Visualization**: View pickup and dropoff locations, as well as the exact path taken on the map.
    *   **Fare Audit**: See the exact breakdown of base fare, distance fee, time fee, and any surge pricing multipliers.

### 📦 Delivery Hub
*   **Purpose**: Manages package delivery requests.
*   **Features**:
    *   **Parcel Details**: View weight, category (e.g., Fragile, Document), and recipient contact info.
    *   **Proof of Delivery**: Access photos uploaded by drivers upon successful drop-off.
    *   **Configuration**: Standard categories, weight ranges, and vehicle rates can be configured under the Delivery Options section.

### 🚗 Vehicle Fleet
*   **Purpose**: The registry of all authorized vehicles on the platform.
*   **Features**:
    *   **Type Assignment**: Assign vehicles to categories like *Go*, *Pragya*, or *Comfort*.
    *   **Document Vault**: Audit insurance and roadworthy certificates.
    *   **Verification**: Toggle a vehicle's status to allow it to start receiving ride requests.

### 💳 Wallets & Payments
*   **Purpose**: Financial ledger for the entire platform.
*   **Features**:
    *   **Transaction Logs**: Search for specific payment reference numbers to troubleshoot failures.
    *   **Manual Adjustments**: Credit or debit user wallets for compensation or debt recovery.

---

## 2. Growth & Marketing (Revenue Drivers)
Tools to scale the user base and monetize the platform.

### 📢 Ad Management
*   **Purpose**: Manage in-app advertising slots.
*   **Features**:
    *   **Creative Review**: Preview the headline, text, and images submitted by business partners.
    *   **Scheduling**: Approve ads to run during specific weeks.
    *   **Ad Slots**: Configure the maximum number of ads allowed per week and set their pricing.

### 🎫 Promos & Coupons
*   **Purpose**: Incentivize riders with discounts.
*   **Features**:
    *   **Discount Types**: Set percentage discounts (e.g., 20% off) or flat amounts (e.g., 5 GHS off).
    *   **Redemption Limits**: Restrict usage per user or cap the total number of times a code can be used across the platform.

### 🚀 Campaigns
*   **Purpose**: Manage the visual announcements on the mobile home screen.
*   **Features**:
    *   **Banner Placement**: Upload high-resolution images for the home screen slider.
    *   **App Linking**: Set a destination link to send users to a specific part of the app or an external website when they tap the banner.

---

## 3. Security & Support (Trust & Safety)
Maintaining the integrity and safety of the platform.

### ⚠️ Incident Hub
*   **Purpose**: Real-time management of SOS alerts and safety reports.
*   **Features**:
    *   **Urgency Levels**: Categorize reports as *Low*, *Medium*, or *Critical*.
    *   **Audit Log**: Document every step of the investigation and resolution process.

### 🚫 Fraud Flags
*   **Purpose**: Proactive identification of suspicious activity.
*   **Features**:
    *   **Automated Triggers**: See alerts generated for "GPS spoofing" (faking locations) or "Duplicate Device ID" attempts.
    *   **User Ban**: Quickly suspend a user's account if fraud is confirmed.

### 🆔 Driver Verifications
*   **Purpose**: The gatekeeper for driver onboarding.
*   **Features**:
    *   **Document Review**: Verify National IDs, Driving Licenses, and Background Checks.
    *   **Verification Status**: Move drivers through the `Pending` → `In Progress` → `Approved` cycle.

---

## 4. System & Content (Global Configuration)
Fine-tuning the platform's behavior and marketing presence.

### 🌐 Global Settings
*   **Purpose**: Master switches for the entire ecosystem.
*   **Key Features**:
    *   **Country Search Restriction**: Enter country abbreviations (e.g., `gh` for Ghana, `ng` for Nigeria) to lock the address search feature to specific countries.
    *   **Surge Pricing Toggle**: A master switch to turn real-time demand-based pricing on or off globally.
    *   **Automated Push Notifications**: Customize the messages for system-generated alerts:
        *   **Welcome Message**: The title and text sent when a user registers for the first time.
        *   **Birthday Message**: The title and text sent to drivers annually on their birthday.

### 💰 Pricing Rules
*   **Purpose**: Define how much a ride costs.
*   **Features**:
    *   **City-Specific Rates**: Set different base fares and per-kilometer rates for different cities (e.g., Accra vs. Kumasi).
    *   **Distance Tiers**: Set higher rates for long-distance trips.

### 📦 Delivery Options
*   **Purpose**: Define the options and pricing rules for parcel deliveries.
*   **Features**:
    *   **Delivery Categories**: Add or modify package categories (e.g. *Documents*, *Food*, *Electronics*) and set percentage price markups.
    *   **Weight Tiers**: Configure weight ranges (e.g. *Light*, *Medium*, *Heavy*) and their percentage price markups.
    *   **Delivery Vehicle Types**: Set base fares and per-kilometer rates for different delivery vehicles (e.g. *Motorcycle*, *Bicycle*, *Car*).

### 📝 Website Editor
*   **Blog Posts**: Create content to drive traffic to your website.
*   **FAQ Items**: Update common questions for riders and drivers.
*   **Cities**: Update the marketing site with new regions you've launched in.
*   **Hero Banners**: Change the main background images on the marketing website.

### ☁️ File Cloud
*   **Purpose**: Centralized management of all uploaded media.
*   **Features**:
    *   **Access Control**: Monitor who uploaded what file and when.
    *   **Storage Audit**: Track the total volume of driver documents and marketing assets stored on the servers.

---

## 5. Audit & Developers
Technical logs and integration controls.

### 📜 System Audit Logs
*   **Purpose**: Accountability for admin actions.
*   **Features**:
    *   **Change History**: See exactly which admin modified a pricing rule, deleted a user, or changed a setting.

### 🔑 Third-Party Integrations
*   **Purpose**: Managing external technical partnerships.
*   **Features**:
    *   **Secret Keys**: Generate and manage access keys for third-party partners (e.g., dispatchers or aggregators) who need to connect to the system.

---

> [!IMPORTANT]
> **Safety First**: Changing a **Pricing Rule** or **Global Setting** affects the entire live platform instantly. Always double-check values before saving.
