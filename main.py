import re
import os
import requests
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import datetime
from urllib.parse import urlparse
import threading
import smtplib
import chromedriver_autoinstaller
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import mysql.connector

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# MySQL database configuration
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

# Selenium WebDriver setup with optimized anti-CAPTCHA settings
chromedriver_autoinstaller.install()  # Automatically install the correct version of ChromeDriver

# Function to create optimized Chrome options for CAPTCHA bypass
def get_optimized_chrome_options():
    options = Options()
    
    # Essential settings to bypass CAPTCHA detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Set a common user agent
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Uncomment if you want to run headless (but this might increase CAPTCHA chances)
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    return options

app = Flask(__name__)

# Set the secret key for session management
app.secret_key = os.getenv('SECRET_KEY')

# Email configuration
EMAIL_SENDER = os.getenv('EMAIL_SENDER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

# Function to send email notifications
def send_email(subject, body, receiver_email):
    try:
        # Setup the SMTP server
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()  # Start TLS encryption
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)  # Login with App Password
            # Format the email message with UTF-8 encoding
            message = f"Subject: {subject}\nContent-Type: text/plain; charset=utf-8\n\n{body}".encode("utf-8")
            # Send the email
            server.sendmail(EMAIL_SENDER, receiver_email, message)
            print(f"Email sent successfully: {subject}")
    except smtplib.SMTPAuthenticationError:
        print("Authentication error: Check your email and app password.")
    except Exception as e:
        print(f"Failed to send email: {e}")

# Connect to the database
def connect_to_db():
    try:
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            print("Successfully connected to the database")
            return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

# Function to create the ProductDetails, Content, and History tables if they don't exist
def create_tables():
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ProductDetails (
                id INT AUTO_INCREMENT PRIMARY KEY,
                site VARCHAR(255) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                product_name VARCHAR(255) NOT NULL,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Content (
                id INT AUTO_INCREMENT PRIMARY KEY,
                price DECIMAL(10, 2) NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS History (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                url VARCHAR(255) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
        cursor.close()
        connection.close()
        print("Tables ProductDetails, Content, and History created successfully.")
    except mysql.connector.Error as err:
        print(f"Error creating tables: {err}")

# Function to delete previous data from the ProductDetails and Content tables
def delete_previous_data():
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM ProductDetails")
        cursor.execute("DELETE FROM Content")
        connection.commit()
        cursor.close()
        connection.close()
        print("Previous data deleted successfully.")
    except mysql.connector.Error as err:
        print(f"Error deleting data from database: {err}")

# Function to delete previous data from the Content table
def delete_previous_content_data():
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM Content")
        connection.commit()
        cursor.close()
        connection.close()
        print("Previous data in Content table deleted successfully.")
    except mysql.connector.Error as err:
        print(f"Error deleting data from Content table: {err}")

# Function to save full URL, price, and product name in the ProductDetails table
def save_to_database(site, price, product_name):
    try:
        connection = connect_to_db()
        cursor = connection.cursor()

        # Remove currency symbols before inserting into the database
        numeric_price = re.sub(r"[^\d.]", "", price)

        query = "INSERT INTO ProductDetails (site, price, product_name, scraped_at) VALUES (%s, %s, %s, NOW())"
        values = (site, numeric_price, product_name)
        cursor.execute(query, values)

        connection.commit()
        cursor.close()
        connection.close()
    except mysql.connector.Error as err:
        print(f"Error saving to database: {err}")

# Function to save unique prices in the Content table
def save_prices_to_content(prices):
    try:
        connection = connect_to_db()
        cursor = connection.cursor()

        for price in prices:
            numeric_price = re.sub(r"[^\d.]", "", price)
            query = "INSERT INTO Content (price) VALUES (%s)"
            cursor.execute(query, (numeric_price,))

        connection.commit()
        cursor.close()
        connection.close()
    except mysql.connector.Error as err:
        print(f"Error saving prices to Content table: {err}")

# Function to save email, URL, and price in the History table
def save_to_history(email, url, price):
    try:
        connection = connect_to_db()
        cursor = connection.cursor()

        # Check for duplicate entries
        query = "SELECT * FROM History WHERE email = %s AND url = %s AND price = %s"
        cursor.execute(query, (email, url, price))
        result = cursor.fetchone()

        if result:
            print(f"Duplicate entry found for email: {email}, url: {url}, price: {price}. Skipping insertion.")
            cursor.close()
            connection.close()
            return False
        else:
            query = "INSERT INTO History (email, url, price, scraped_at) VALUES (%s, %s, %s, NOW())"
            values = (email, url, price)
            cursor.execute(query, values)
            connection.commit()
            print(f"Entry added to history for email: {email}, url: {url}, price: {price}.")
            cursor.close()
            connection.close()
            return True
    except mysql.connector.Error as err:
        print(f"Error saving to history: {err}")
        return False

# Function to read prices from the Content table
def read_prices_from_content():
    prices_in_db = []
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        cursor.execute("SELECT price FROM Content")
        results = cursor.fetchall()
        for row in results:
            prices_in_db.append(row[0])
        cursor.close()
        connection.close()
    except mysql.connector.Error as err:
        print(f"Error reading prices from Content table: {err}")
    return prices_in_db

# The function to get the last price from the History table
def get_price_from_history(url):
    conn = connect_to_db()
    if conn is None:
        print("Database connection failed")
        return None

    try:
        cursor = conn.cursor()
        query = "SELECT price FROM History WHERE url = %s ORDER BY scraped_at DESC LIMIT 1"
        cursor.execute(query, (url,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            price = result[0]
            # Normalize price to float
            return float(price)
        else:
            print(f"No price found in history for URL: {url}")
            return None
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        if conn.is_connected():
            conn.close()
        return None

# Function to get price and scraped_at from ProductDetails
def get_price_and_scraped_at_from_productdetails(url):
    conn = connect_to_db()
    if conn is None:
        print("Database connection failed")
        return None, None

    try:
        cursor = conn.cursor()
        query = "SELECT price, scraped_at FROM ProductDetails WHERE site = %s ORDER BY scraped_at DESC LIMIT 1"
        cursor.execute(query, (url,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            price, scraped_at = result
            return float(price), scraped_at
        else:
            print(f"No price found in ProductDetails for URL: {url}")
            return None, None
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        if conn.is_connected():
            conn.close()
        return None, None

# Function to log comparison results
def log_result(message, price, site_url):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{message} - Price: ₹{price} for site {site_url} at {timestamp}")

    # Send email notification for price changes
    if message == "price changed":
        email_subject = "Price Change Alert"
        email_body = f"Hii there, \n\nWe've detected a price change on {site_url}. \n\nThis update was recorded on {timestamp}. \n\nMake sure to check the site for the latest pricing details and take advantage of any new deals or offers!"
        send_email(email_subject, email_body, user_email)

    if message == "found a match":
        email_subject = "No change Alert"
        email_body = f"Hii there, \n\nWe've not detected any price change on {site_url}. \n\nThis update was recorded on {timestamp}."
        send_email(email_subject, email_body, user_email)

# Function to check and log prices - UPDATED with optimized CAPTCHA bypass
def check_and_log_price(url):
    """
    Capture all visible content with INR symbol, filter duplicates, and write it to the Content table.
    """
    try:
        # Get optimized Chrome options for CAPTCHA bypass
        options = get_optimized_chrome_options()
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        # Execute stealth JavaScript before loading the page
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Visit the URL
        driver.get(url)
        
        # Clear the Content table before adding new prices
        delete_previous_content_data()
        print("Previous entries in Content table deleted")

        all_content = set()  # Use a set to store unique prices

        # Wait for elements to be present
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, "//*")))

        elements = driver.find_elements(By.XPATH, "//*")  # Fetch all elements on the page

        for element in elements:
            try:
                text = element.text.strip()
                # Join lines to handle multi-line text
                clean_text = " ".join(text.split())
                # Remove non-relevant prefixes like "Price:"
                clean_text = re.sub(r'Price:\s*', '', clean_text)
                # Extract price using regex
                price_match = re.search(r'(₹|Rs\.?|\$)\s*(\d+(\.\d{1,2})?)', clean_text)
                if price_match:
                    price = price_match.group(2)  # Extract the numeric part of the price
                    all_content.add(price)  # Add price to the set
            except Exception as e:
                continue  # Ignore errors

        # Save unique prices to the Content table
        save_prices_to_content(all_content)
        print(f"Unique prices written to Content table")

    except Exception as e:
        print(f"Error extracting and storing content: {e}")
    finally:
        driver.quit()

# Function to compare a specific site's price from the history with Content table prices
def compare_site_price_with_content(site_url):
    db_price = get_price_from_history(site_url)
    if db_price is None:
        print(f"No price found in the history for site: {site_url}")
        return

    db_price_str = f"{db_price:.2f}"
    db_prices = read_prices_from_content()

    # Check if db_prices is empty
    if not db_prices:
        raise ValueError(f"No prices found in Content table for site: {site_url}. Please verify the scraping process.")

    # Convert db_prices to a standardized format
    db_prices = [f"{float(price):.2f}" for price in db_prices]

    # Compare database price with prices in Content table
    if db_price_str in db_prices:
        log_result("found a match", db_price, site_url)
    else:
        log_result("price changed", db_price, site_url)

# Function to start tracing prices for a URL with periodic checks
def start_price_tracing(url):
    total_checks = 2
    check_interval = 30  # 24 hours in seconds
    check_count = 0

    while check_count < total_checks:
        try:
            print(f"Starting trace #{check_count + 1} for {url}")
            time.sleep(4)  # wait for 4 sec to load the page
            check_and_log_price(url)
            compare_site_price_with_content(url)

            check_count += 1

            if check_count < total_checks:
                print(f"Waiting for {check_interval} seconds before next trace.")
                time.sleep(check_interval)  # Wait for 24 hours before the next trace

        except Exception as e:
            print(f"Error during price tracing for {url}: {e}")
            break

    # Remove the row from the history table after completing all traces
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        query = "DELETE FROM History WHERE url = %s"
        cursor.execute(query, (url,))
        connection.commit()
        cursor.close()
        connection.close()
        print(f"Removed entry from history for url: {url}")
    except mysql.connector.Error as err:
        print(f"Error removing entry from history: {err}")

    print(f"Completed {total_checks} traces for {url}. Stopping price tracing.")

# Function to scrape product details from Google using the barcode - UPDATED with optimized CAPTCHA bypass
def scrape_product_details(barcode_data):
    # Get optimized Chrome options for CAPTCHA bypass
    options = get_optimized_chrome_options()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    # Execute stealth JavaScript before loading the page
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # Modify the window.navigator object to hide automation
    driver.execute_script("""
    const newProto = navigator.__proto__;
    delete newProto.webdriver;
    navigator.__proto__ = newProto;
    """)
    
    # Set a custom plugin array to make fingerprinting more difficult
    driver.execute_script("""
    Object.defineProperty(navigator, 'plugins', {
        get: function() { return [1, 2, 3, 4, 5]; }
    });
    """)
    
    # Set a custom language array
    driver.execute_script("""
    Object.defineProperty(navigator, 'languages', {
        get: function() { return ['en-US', 'en']; }
    });
    """)
    
    url = f'https://www.google.com/search?q={barcode_data}'
    driver.get(url)
    
    website_data = []
    seen_products = set()
    
    # Use a more efficient approach with fewer pages
    max_pages = 3  # Limit to 3 pages for faster results
    
    for page in range(max_pages):
        try:
            # Wait for the search results to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div:has(span.VuuXrf)"))
            )
            
            site_blocks = driver.find_elements(By.CSS_SELECTOR, "div:has(span.VuuXrf)")
            
            for block in site_blocks:
                try:
                    link_element = block.find_element(By.TAG_NAME, "a")
                    full_url = link_element.get_attribute('href')

                    product_name_element = block.find_element(By.CSS_SELECTOR, "h3")
                    product_name = product_name_element.text.strip()

                    try:
                        price_element = block.find_element(By.CSS_SELECTOR, "span.LI0TWe.wHYlTd")
                        price = price_element.text.strip()
                    except:
                        price = None

                    # Extract image source
                    image_element = block.find_element(By.CSS_SELECTOR, "img.XNo5Ab")
                    image_src = image_element.get_attribute('src')

                    # Handle price ranges
                    if price and "to" in price:
                        price_range = price.split(" to ")
                        price = price_range[1]

                    if full_url and product_name and price:
                        parsed_url = urlparse(full_url)
                        base_domain = parsed_url.netloc

                        product_key = (base_domain, product_name, price, full_url)
                        if product_key not in seen_products:
                            website_data.append({
                                "site": base_domain,
                                "product": product_name,
                                "price": price,
                                "url": full_url,
                                "image_src": image_src  # Add image source to the data
                            })
                            seen_products.add(product_key)
                            # Save to database now including product_name
                            save_to_database(full_url, price, product_name)
                except Exception as e:
                    print(f"Error processing block: {e}")
                    continue
            
            # Try to go to the next page if not on the last page
            if page < max_pages - 1:
                next_button = driver.find_element(By.XPATH, "//span[text()='Next']")
                next_button.click()
                # Wait a short time for the next page to load
                time.sleep(2)
        except Exception as e:
            print(f"Error on page {page+1}: {e}")
            break
    
    driver.quit()
    return website_data

# Global variable for user email
user_email = None

# Route to start the barcode scan and scraping process
@app.route('/scan_and_scrape', methods=['POST'])
def scan_and_scrape():
    delete_previous_content_data()
    data = request.get_json()
    barcode_data = data.get('barcode')
    print(f"Barcode Scanned: {barcode_data}")  # Debugging line

    if barcode_data:
        # Proceed with scraping product details
        product_details = scrape_product_details(barcode_data)
        return jsonify(product_details)
    else:
        return jsonify({"error": "No barcode detected"})

# Route to start tracing for a specific product
@app.route("/start_tracing/<path:url>")
def start_tracing(url):
    threading.Thread(target=start_price_tracing, args=(url,), daemon=True).start()
    return jsonify({"message": f"Started tracing for {url}\n\n Check your email for updates."})

# Route to render the main HTML page
@app.route('/')
def index():
    username = session.get('username')  # Retrieve username from session if logged in
    return render_template('index.html', username=username)

# Route to handle email input from the user
@app.route('/set_email', methods=['POST'])
def set_email():
    global user_email  # Use the global variable to store email
    user_email = request.form.get('email')  # Get email from the form input
    print(f"User's email set to: {user_email}")
    return redirect(url_for('index'))

# Route to handle trace button click and save to history
@app.route('/trace/<path:url>', methods=['POST'])
def trace(url):
    price, scraped_at = get_price_and_scraped_at_from_productdetails(url)
    if price is not None and scraped_at is not None:
        if save_to_history(user_email, url, price):
            threading.Thread(target=start_price_tracing, args=(url,), daemon=True).start()
            return jsonify({"message": "Trace started successfully. Check your email for updates."})
        else:
            return jsonify({"message": "Trace already exists. Skipping insertion."}), 400
    else:
        return jsonify({"message": "Failed to start trace. Price not found."}), 400

if __name__ == "__main__":
    create_tables()  # Create tables if they don't exist
    delete_previous_data()  # Delete previous data
    app.run(debug=True)