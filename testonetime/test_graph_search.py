from scraper.graph_search import app_search
import os
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    test_input = {
        "question": "Berapa harga buah alpukat per 1 kg di Jakarta dan kota lainnya di Indonesia dalam mata uang Rupiah ?"
    }

    result = app_search.invoke(test_input)

    print("Graph execution result:")
    print(result)