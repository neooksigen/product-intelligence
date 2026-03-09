#This function safe_extract_item will not be as Node. It is just helper function.
def safe_extract_item(response):
    if isinstance(response, str):
        # "'Rp 20000'" → 'Rp 20000'
        if response.startswith("'") and response.endswith("'"):
            return response[1:-1]
        return response
    
    elif isinstance(response, list) and len(response) > 0:
        # "['Rp 20000']" → 'Rp 20000'
        item = response[0]
        if isinstance(item, str) and item.startswith("'") and item.endswith("'"):
            return item[1:-1]
        return str(item)
    
    return str(response) 

from urllib.parse import urlsplit, urlunsplit, quote

def normalize_url(url):
    parts = urlsplit(url)
    path = quote(parts.path)
    query = quote(parts.query, safe="=&")

    return urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))