from scraper.graph_gsc import app_gsc
import os
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    test_input = {
        #"user_ask": "Buah paprika per 1 kg"
        #"user_ask": "Bawang merah 1 kg"
        "user_ask": "telur ayam 1 kg"
    }

    result = app_gsc.invoke(test_input)

    print("Graph execution result:")
    print(result)