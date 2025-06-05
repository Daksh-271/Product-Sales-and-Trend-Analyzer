import mysql.connector
import pandas as pd
import numpy as np
import re

def connect_to_db():
    return mysql.connector.connect(host="localhost",port=3306,database="myntradb",user="root",password="root")

def preprocess_myntra_data():
    try:
        db = connect_to_db()
        cursor = db.cursor(dictionary=True)
        
        create_cleaned_table(cursor)
        db.commit()
        
        print("Reading data from myntra_products table...")
        cursor.execute("SELECT * FROM myntra_products")
        rows = cursor.fetchall()
        
        if not rows:
            print("No data found in myntra_products table")
            return
            
        df = pd.DataFrame(rows)
        print(f"Loaded {len(df)} rows for preprocessing")
        
        df_cleaned = preprocess_dataframe(df)
        
        upsert_cleaned_data(df_cleaned, cursor, db)
        
        print(f"Successfully processed {len(df_cleaned)} rows into cleaned_products table")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if db:
            cursor.close()
            db.close()

def create_cleaned_table(cursor):
    cursor.execute("""CREATE TABLE IF NOT EXISTS cleaned_products (id INT PRIMARY KEY,brand VARCHAR(255),name VARCHAR(255),price FLOAT,original_price FLOAT,discount FLOAT,rating FLOAT,category VARCHAR(100),subcategory VARCHAR(100))""")
    

def preprocess_dataframe(df):
    print("Starting preprocessing...")
    
    df_cleaned = df.drop(['image_url', 'product_url', 'created_at'], axis=1, errors='ignore')
    
    df_cleaned['price'] = df_cleaned['price'].apply(lambda x: clean_price(x) if x else np.nan)
    
    df_cleaned['original_price'] = df_cleaned['original_price'].apply(lambda x: clean_price(x) if x else np.nan)
    
    mean_original_price = df_cleaned.loc[df_cleaned['original_price'].notna(), 'original_price'].mean()
    
    print(f"Filling missing original_price values")
    for idx, row in df_cleaned.iterrows():
        if pd.isna(row['original_price']):
            if pd.notna(row['price']) and row['price'] > 0:
                df_cleaned.at[idx, 'original_price'] = row['price']
            else:
                df_cleaned.at[idx, 'original_price'] = mean_original_price
    
    df_cleaned['discount'] = df_cleaned['discount'].apply(lambda x: clean_discount(x) if x else np.nan)
    
    print("Calculating missing discount values...")
    for idx, row in df_cleaned.iterrows():
        if pd.isna(row['discount']):
            if pd.notna(row['price']) and pd.notna(row['original_price']):
                if row['original_price'] > row['price']:
                    discount_pct = ((row['original_price'] - row['price']) / row['original_price']) * 100
                    df_cleaned.at[idx, 'discount'] = round(discount_pct, 2)
                else:
                    df_cleaned.at[idx, 'discount'] = 0.0
    
    df_cleaned['rating'] = df_cleaned['rating'].apply(lambda x: float(x) if x and str(x).strip() else np.nan)
    
    mean_rating = df_cleaned.loc[df_cleaned['rating'].notna(), 'rating'].mean()
    
    df_cleaned['rating'] = df_cleaned['rating'].fillna(mean_rating)
    
    df_cleaned['id'] = df_cleaned['id'].astype(int)
    
    df_cleaned['discount'] = df_cleaned['discount'].fillna(0.0)
    
    return df_cleaned

def clean_price(price_str):
    if not price_str:
        return np.nan
    
    match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)', str(price_str))
    if match:
        return float(match.group(1).replace(',', ''))
    return np.nan

def clean_discount(discount_str):
    if not discount_str:
        return np.nan
    
    match = re.search(r'(\d+(?:\.\d+)?)', str(discount_str))
    if match:
        return float(match.group(1))
    return np.nan

def upsert_cleaned_data(df, cursor, db):
    print("Inserting or updating cleaned data in the table...")
    
    processed_count = 0
    for _, row in df.iterrows():
        try:
            cursor.execute("SELECT id FROM cleaned_products WHERE id = %s", (int(row['id']),))
            exists = cursor.fetchone()
            
            if exists:
                cursor.execute("""UPDATE cleaned_products SET brand = %s, name = %s, price = %s, original_price = %s, discount = %s, rating = %s, category = %s, subcategory = %sWHERE id = %s""", (row['brand'],row['name'],float(row['price']),float(row['original_price']),float(row['discount']),float(row['rating']),row['category'],row['subcategory'],int(row['id'])))
            else:
                cursor.execute("""INSERT INTO cleaned_products (id, brand, name, price, original_price, discount, rating, category, subcategory)VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""", (int(row['id']),row['brand'],row['name'],float(row['price']),float(row['original_price']),float(row['discount']),float(row['rating']),row['category'],row['subcategory']))
            
            db.commit()
            processed_count += 1
            
            if processed_count % 100 == 0:
                print(f"Processed {processed_count} records...")
                
        except Exception as e:
            print(f"Error processing row {row['id']}: {str(e)}")
            
    print(f"Total records processed: {processed_count}")

if __name__ == "__main__":
    print("MYNTRA's DATA PREPROCESSING")
    preprocess_myntra_data()
    print("Process completed.")