from app.database_sqlalchemy import engine
import pandas as pd
from sqlalchemy import text

#test_data = pd.DataFrame([
#    {
#        "product_name": "Test Demo 00",
#        "quantity": "1",  
#        "measurement_scale": "kg",              
#        "price": "Rp 74.000",
#        "source": "E-commerce sites",
#        "rating": "5",        
#        "review_count": "100",
#        "place": "Indonesia",
#        "method": "search",
#        "source_date": "2026-01-01",
#        "timestamp_extract": "2026-02-17 13:30"
#    }
#])
#test_data.to_sql("products", engine, if_exists="append", index=False)
#print("Inserted successfully!")

def test_insert():
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO products (
                product_name, quantity, measurement_scale, price, source, rating, review_count, place, method, source_date, timestamp_extract
            ) VALUES (
                'Test Demo 00', '1', 'kg', 'Rp 74.000', 'E-commerce sites', '5', '100', 'Indonesia', 'search', '2026-01-01', '2026-02-17 13:30' 
            )
        """))
        conn.commit()

    print("Inserted successfully!")

if __name__ == "__main__":
    test_insert()
