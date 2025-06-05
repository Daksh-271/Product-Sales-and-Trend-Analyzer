import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin
import time
import mysql.connector
import re

class MyntraScraper:
    BASE_URL = "https://www.myntra.com"
    
    CATEGORY_MAP = {
        "Topwear": {
            "T-Shirts": "/men-tshirts", "Casual Shirts": "/men-casual-shirts", "Formal Shirts": "/men-formal-shirts", "Sweatshirts": "/men-sweatshirts"
        },
        "Bottomwear": {
            "Jeans": "/men-jeans", "Casual Trousers": "/men-casual-trousers", "Shorts": "/men-shorts", "Track Pants & Joggers": "/men-track-pants-joggers"
        },
        "Footwear": {
            "Casual Shoes": "/men-casual-shoes", "Sports Shoes": "/men-sports-shoes", "Formal Shoes": "/men-formal-shoes", "Sneakers": "/men-sneakers"
        },
        "Sports & Active Wear": {
            "Sports Shoes": "/men-sports-shoes", "Active T-Shirts": "/men-active-tshirts", "Track Pants & Shorts": "/men-track-pants-shorts", "Tracksuits": "/men-tracksuits"
        },
        "Indian & Festive Wear": {
            "Kurtas & Kurta Sets": "/men-kurtas", "Sherwanis": "/sherwani", "Nehru Jackets": "/nehru-jackets", "Dhotis": "/dhoti"
        },
        "Fashion Accessories": {
            "Wallets": "/men-wallets", "Belts": "/men-belts", "Perfumes & Body Mists": "/perfumes", "Trimmers": "/trimmer", "Deodorants": "/deodorant", "Caps & Hats": "/men-caps"
        },
        "Gadgets": {
            "Smart Wearables": "/smart-wearables", "Fitness Gadgets": "/smart-wearables", "Headphones": "/headphones", "Speakers": "/speakers"
        }
    }


    def __init__(self, headless=True):
        options = webdriver.ChromeOptions()
        if headless: options.add_argument("--headless=new")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        self.wait = WebDriverWait(self.driver, 10)
        
        self.db = mysql.connector.connect(host="localhost", port=3306, database="myntradb", user="root", password="root")
        self.cursor = self.db.cursor()
        self.setup_db()
        
        self.all_records_deleted = False

    def setup_db(self):
        sql_query = """CREATE TABLE IF NOT EXISTS myntra_products (id INT AUTO_INCREMENT PRIMARY KEY, brand VARCHAR(255), name VARCHAR(255), price VARCHAR(50), original_price VARCHAR(50), discount VARCHAR(20), rating VARCHAR(10), image_url TEXT, product_url TEXT, category VARCHAR(100), subcategory VARCHAR(100), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)"""
        self.cursor.execute(sql_query)
        
        try:
            self.cursor.execute("""SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'myntradb' AND TABLE_NAME = 'myntra_products' AND COLUMN_NAME = 'updated_at'""")
            if not self.cursor.fetchone():
                self.cursor.execute("""ALTER TABLE myntra_products ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP""")
        except:
            pass
            
        self.db.commit()

    def extract(self, elem, selector, attr=None):
        selectors = selector.split(",")
        for sel in selectors:
            try:
                found = elem.find_element(By.CSS_SELECTOR, sel.strip())
                return found.get_attribute(attr) if attr else found.text.strip()
            except:
                continue
        return ""

    def clean_price(self, price_text):
        if not price_text:
            return ""
        
        match = re.search(r'Rs\.\s*(\d+(?:,\d+)*)', price_text)
        if match:
            return f"Rs. {match.group(1)}"
        return price_text

    def extract_prices_and_discount(self, elem):
        price_elem = self.extract(elem, "div.product-price, span.product-discountedPrice")
        current_price = self.clean_price(price_elem)
        
        original_price_elem = self.extract(elem, "span.product-strike, span.product-mrp")
        original_price = self.clean_price(original_price_elem)
        
        discount = ""
        if original_price and current_price and original_price != current_price:
            try:
                current_val = float(current_price.replace('Rs.', '').replace(',', '').strip())
                original_val = float(original_price.replace('Rs.', '').replace(',', '').strip())
                
                if original_val > current_val > 0:
                    discount_pct = round((original_val - current_val) / original_val * 100)
                    if discount_pct > 0:
                        discount = f"{discount_pct}%"
            except:
                pass
                
        return current_price, original_price, discount

    def extract_rating(self, elem):
        try:
            rating = self.extract(elem, "div.product-ratingsContainer, span.product-rating, div.product-rating")
            if rating:
                match = re.search(r'(\d+\.?\d*)', rating)
                if match:
                    return match.group(1)
            return ""
        except:
            return ""
            
    def clean_database_for_category(self, category, subcategory):
        try:
            self.cursor.execute("""SELECT COUNT(*) FROM myntra_products WHERE category = %s AND subcategory = %s""", (category, subcategory))
            
            count = self.cursor.fetchone()[0]
            if count > 0:
                print(f"Found {count} existing products for {category} > {subcategory}")
                
                choice = input("Choose an option:\n1. Delete existing records\n2. Keep and update existing records\nChoice (1/2): ").strip()
                
                if choice == '1':
                    self.cursor.execute("""DELETE FROM myntra_products WHERE category = %s AND subcategory = %s""", (category, subcategory))
                    
                    self.cursor.execute("ALTER TABLE myntra_products AUTO_INCREMENT = 1")
                    
                    self.db.commit()
                    print(f"Deleted {count} existing products")
                    self.all_records_deleted = True
                    return "deleted", count
                elif choice == '2':
                    self.all_records_deleted = False
                    return "kept", count
                else:
                    print("Invalid choice, keeping existing records")
                    self.all_records_deleted = False
                    return "kept", count
        except Exception as e:
            print(f"Database cleanup error: {str(e)}")
        
        self.all_records_deleted = False
        return "none", 0

    def process_product(self, product_data):
        brand, name, price, original_price, discount = product_data[:5]
        rating, image_url, product_url, category, subcategory = product_data[5:]
        
        if self.all_records_deleted:
            try:
                self.cursor.execute("""INSERT INTO myntra_products (brand, name, price, original_price, discount, rating, image_url, product_url, category, subcategory)VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", (brand, name, price, original_price, discount, rating, image_url, product_url, category, subcategory))
                return "inserted"
            except Exception as e:
                print(f"Database insert error: {str(e)}")
                return "error"
        
        try:
            self.cursor.execute("""SELECT id FROM myntra_products WHERE brand = %s AND name = %s AND product_url = %s AND category = %s AND subcategory = %s""", (brand, name, product_url, category, subcategory))
            
            result = self.cursor.fetchone()
            
            if result:
                product_id = result[0]
                self.cursor.execute("""UPDATE myntra_products SET price = %s, original_price = %s, discount = %s, rating = %s, image_url = %sWHERE id = %s""", (price, original_price, discount, rating, image_url, product_id))
                return "updated"
            else:
                self.cursor.execute("""INSERT INTO myntra_products (brand, name, price, original_price, discount, rating, image_url, product_url, category, subcategory)VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", (brand, name, price, original_price, discount, rating, image_url, product_url, category, subcategory))
                return "inserted"
                
        except Exception as e:
            print(f"Database upsert error: {str(e)}")
            return "error"

    def scrape(self, url, category, subcategory, max_pages=3):
        action, count = self.clean_database_for_category(category, subcategory)
        
        products_inserted = 0
        products_updated = 0
        
        for page in range(1, max_pages + 1):
            try:
                page_url = f"{urljoin(self.BASE_URL, url)}{'?p=' + str(page) if page > 1 else ''}"
                self.driver.get(page_url)
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.product-base")))
                time.sleep(1.5)
                
                products_on_page = self.driver.find_elements(By.CSS_SELECTOR, "li.product-base")
                if not products_on_page:
                    print(f"No products found on page {page}. Stopping.")
                    break
                
                page_inserted = 0
                page_updated = 0
                    
                for elem in products_on_page:
                    try:
                        brand = self.extract(elem, "h3.product-brand")
                        name = self.extract(elem, "h4.product-product")
                        
                        price, original_price, discount = self.extract_prices_and_discount(elem)
                        
                        rating = self.extract_rating(elem)
                        
                        image_url = self.extract(elem, "img.img-responsive", "src")
                        product_url = urljoin(self.BASE_URL, self.extract(elem, "a", "href"))
                        
                        if not brand or not name or not price:
                            continue
                        
                        product_data = (brand, name, price, original_price, discount, rating, image_url, product_url, category, subcategory)
                        
                        result = self.process_product(product_data)
                        if result == "inserted":
                            products_inserted += 1
                            page_inserted += 1
                        elif result == "updated":
                            products_updated += 1
                            page_updated += 1
                            
                        self.db.commit()
                        
                    except Exception as e:
                        print(f"Product error: {str(e)[:50]}...")
                
                print(f"Page {page}: Inserted {page_inserted}, Updated {page_updated} products")
                
            except Exception as e:
                print(f"Page error: {str(e)[:50]}...")
                break
                
        return products_inserted, products_updated

    def close(self):
        self.driver.quit()
        self.db.close()

def show_menu(options):
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")
    print("0. Exit")
    
    while True:
        try:
            choice = int(input("Choice: "))
            if 0 <= choice <= len(options):
                return choice
            print(f"Enter 0-{len(options)}")
        except ValueError:
            print("Numbers only!")

def main():
    scraper = MyntraScraper(headless=False)
    
    try:
        cats = list(scraper.CATEGORY_MAP.keys())
        print("\nMAIN CATEGORIES:")
        cat_choice = show_menu(cats)
        if cat_choice == 0: return
        
        category = cats[cat_choice-1]
        
        subcats = list(scraper.CATEGORY_MAP[category].keys())
        print(f"\nSUB-CATEGORIES OF {category.upper()}:")
        subcat_choice = show_menu(subcats)
        if subcat_choice == 0: return
        
        subcategory = subcats[subcat_choice-1]
        url = scraper.CATEGORY_MAP[category][subcategory]
        
        try:
            max_pages = int(input("\nEnter max pages to scrape (default 3): ") or 3)
        except ValueError:
            max_pages = 3
        
        print(f"\nScraping {category} > {subcategory}...")
        inserted, updated = scraper.scrape(url, category, subcategory, max_pages)
        print(f"Completed: {inserted} products inserted, {updated} products updated")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        scraper.close()

if __name__ == "__main__":
    print("MYNTRA MEN'S PRODUCT SCRAPER")
    main()