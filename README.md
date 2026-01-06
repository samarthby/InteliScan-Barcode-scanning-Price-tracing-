Perfect 👍
Below is your **updated `README.md` content** with:

✅ **Screenshots section added in between**
❌ **License section removed**
❌ **Author section removed**
✅ Everything else kept **exactly the same style and clarity**

You can **directly copy–paste** this.

---

````md
# Inteliscan – Barcode-Based Product Price Tracker

Inteliscan is a full-stack web application that scans product barcodes using a device camera, scrapes live product prices from the web, stores price history, and notifies users via email when price changes are detected.

---

## 🚀 Features

- 📷 Real-time barcode scanning using device camera  
- 🌐 Automated product & price scraping from Google search results  
- 🧠 CAPTCHA-aware Selenium scraping with stealth configuration  
- 💾 Price history tracking with MySQL database  
- 🔔 Email alerts for price change and no-change events  
- 🔄 Periodic background price monitoring  
- ⚡ Fully asynchronous price tracing using threading  

---

## 🧰 Tech Stack

### Frontend
- HTML5, CSS3
- JavaScript (Vanilla)
- BarcodeDetector API
- MediaDevices (getUserMedia)
- Fetch API

### Backend
- Python
- Flask (REST APIs & routing)
- Selenium WebDriver (Chrome)
- Threading (background tasks)

### Database
- MySQL
- mysql-connector-python

### Automation & Utilities
- ChromeDriver + WebDriver Manager
- chromedriver-autoinstaller
- dotenv (environment variables)
- SMTP (Gmail) for email notifications

---

## 🏗️ System Architecture

1. User scans a barcode using the browser camera  
2. Barcode is sent to Flask backend  
3. Selenium scrapes product details & prices  
4. Prices are stored in MySQL  
5. Periodic checks compare old vs new prices  
6. Email alerts are triggered on price changes  

---

## 🖼️ Screenshots


- Home page with barcode scan option  
- Live barcode scanning using camera  
- Product listing with prices and images  
- Price tracing and email notification flow  

```text
/screenshots
 ├── front.png
 ├── barcode-scan.png
 ├── available_in
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/inteliscan.git
cd inteliscan
````

### 2️⃣ Create a Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔐 Environment Configuration

Create a `.env` file in the project root:

```env
SECRET_KEY=your_secret_key

DB_HOST=localhost
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=inteliscan_db

EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_gmail_app_password
```

⚠️ **Note:** Use a Gmail App Password, not your regular email password.

---

## 🗄️ Database Setup

Ensure MySQL is running and create the database:

```sql
CREATE DATABASE inteliscan_db;
```

Tables are **auto-created** when the application starts.

---

## ▶️ Running the Application

```bash
python app.py
```

Open your browser and visit:

```
http://127.0.0.1:5000
```

---

## 📌 Usage

1. Enter your email address on the homepage
2. Click **Scan Barcode** and allow camera access
3. Scan a product barcode
4. View scraped products and prices
5. Click **Trace** to start price monitoring
6. Receive email alerts when price changes

---

## 🛡️ Notes & Limitations

* Headless scraping may still trigger CAPTCHA on some sites
* Google DOM structure changes may require selector updates
* Price tracking interval is configurable in backend

---

```


