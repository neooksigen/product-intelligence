from scraper.graph_extract import app_extract
import os
from dotenv import load_dotenv
load_dotenv()

url_list = [
    #"https://supermarket.yogyaonline.co.id/supermarket/makanan-sarapan-roti/category"
    #"https://supermarket.yogyaonline.co.id/supermarket/fresh-daging-dan-ayam-ayam-bebek/category"
    #"https://supermarket.yogyaonline.co.id/?search=beras",
    #"https://supermarket.yogyaonline.co.id/supermarket/hot-deals-serba-hemat-02-fresh-setiap-hari/category"
    #"https://order.lottemart.co.id/category/2/sea-water-fish", #not working...
    #"https://order.lottemart.co.id/category/4/local-rice",
    #"https://www.ubifresh.id/market/pd-pasar-jaya-senen/",
    #"https://www.blibli.com/jual/cabe-merah-1-kg",
    'https://www.blibli.com/cari/buah%20segar%20per%201%20kg'
    #'https://www.blibli.com/jual/buah-buahan-segar-1-kg'
    #"https://www.sayurbox.com/category/buah-segar-afghsmue?selectedCategoryType=ops&touch_point=screen_shop&section_source=shop_category_slider_buah-segar-afghsmue&item_index=4"
    #"https://www.astronauts.id/c/ayam-unggas-7179"
    #"https://shopee.co.id/supermarket/Bahan-Pokok-Bumbu-Dapur-cat.11043451.11043467?page=2" #cannot
    #"https://www.klikindomaret.com/xpress/category/makanan/buah-dessert?categories=%5B%5D&page=3" #cannot...
    #"https://www.google.com/search?q=harga+telur+ayam+per+kg+indonesia&num=10&newwindow=1&sca_esv=8b26332a4a3db4ef&udm=28&sxsrf=ANbL-n4tPFt3AfqAwAFRNVkH-T2rYaHVrg%3A1769744934279&shoprs=&ei=Jip8abzbEJyGnesPrY-TkAI&ved=0ahUKEwi8hprRrbKSAxUcQ2cHHa3HBCIQ4dUDCBI&uact=5&oq=harga+telur+ayam+per+kg+indonesia&gs_lp=Ehlnd3Mtd2l6LW1vZGVsZXNzLXNob3BwaW5nIiFoYXJnYSB0ZWx1ciBheWFtIHBlciBrZyBpbmRvbmVzaWFI36cEUKeeBFjIowRwBHgBkAEAmAFIoAHUAqoBATW4AQPIAQD4AQGYAgegAucBwgIKEAAYsAMY1gQYR8ICBxAjGLQEGCfCAgQQIRgKmAMAiAYBkAYIkgcBN6AHkwiyBwEzuAfWAcIHBTIuMi4zyAcQgAgA&sclient=gws-wiz-modeless-shopping" #cannot...
]

if __name__ == "__main__":
    test_input = {
        "urls": url_list
    }

    result = app_extract.invoke(test_input)

    print("Graph execution result:")
    print(result)