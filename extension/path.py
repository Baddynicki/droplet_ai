import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

HOMEPAGE = "https://gcbaijnath.ac.in/"             # Replace with the homepage
TARGET_URL = "https://gcbaijnath.ac.in/general-instructions/"    # Replace with your webpage link

domain = urlparse(HOMEPAGE).netloc

# Queue stores tuples of (current_url, path_taken_to_get_here)
queue = [(HOMEPAGE, [HOMEPAGE])]
visited = set([HOMEPAGE])

print("Analyzing click paths...")

found = False
while queue:
    current_url, path = queue.pop(0)
    
    try:
        response = requests.get(current_url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract all internal links on the current page
        for link in soup.find_all('a', href=True):
            absolute_url = urljoin(current_url, link['href'])
            
            # Normalize URL (remove fragments like #about)
            absolute_url = urlparse(absolute_url)._replace(fragment='').geturl()
            
            if absolute_url == TARGET_URL:
                print("\n[SUCCESS] Path found from homepage!")
                full_path = path + [TARGET_URL]
                for i, step in enumerate(full_path):
                    print(f" Click {i}: {step}")
                found = True
                break
                
            if urlparse(absolute_url).netloc == domain and absolute_url not in visited:
                visited.add(absolute_url)
                queue.append((absolute_url, path + [absolute_url]))
                
    except Exception:
        continue
        
    if found:
        break

if not found:
    print("\nCould not find a direct click path from the homepage. The link might be generated dynamically by JavaScript or hidden in a menu not parsed by standard HTML.")
