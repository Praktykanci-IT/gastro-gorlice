import json
import time
import os
import requests
import logging
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

# --- KONFIGURACJA ŚCIEŻEK ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Ścieżka do folderu public w Twoim projekcie React
REACT_PUBLIC_DIR = os.path.join(BASE_DIR, "react", "gastro-gorlice", "public")

MEDIA_DIR = os.path.join(REACT_PUBLIC_DIR, "gastro_media") 
JSON_OUTPUT = os.path.join(REACT_PUBLIC_DIR, "gastro_data.json")

LOG_FILE = os.path.join(BASE_DIR, "scraper.log")
COOKIES_FILE = os.path.join(BASE_DIR, "cookies.json") 

# Tworzenie bazowego folderu na zdjęcia
os.makedirs(MEDIA_DIR, exist_ok=True)

# --- KONFIGURACJA RESTAURACJI ---
RESTAURANTS = [
    {"name": "Pizzeria Del Piero", "url": "https://www.facebook.com/p/Pizzeria-Del-Piero-100063622118097/"},
    {"name": "Kebap Stambuł", "url": "https://www.facebook.com/p/KEBAP-Stambu%C5%82-new-100057644341776/"},
    {"name": "Restauracja Podzamcze", "url": "https://www.facebook.com/podzamczegorlice/"},
    {"name": "BONA Bistro-Bar", "url": "https://www.facebook.com/803975942806402/"},
    {"name": "Pub Pizzeria Chili", "url": "https://www.facebook.com/PubPizzeriaChili/"},
    {"name": "Bilard Kręgle", "url": "https://www.facebook.com/bilard.kregle/"},
    {"name": "Bar New York", "url": "https://www.facebook.com/barnewyorkgorlice/"},
    {"name": "Bar Mleczny Wojtek", "url": "https://www.facebook.com/p/Bar-mleczny-Wojtek-Gorlice-100063715833727/"},
    {"name": "Lucy Bar", "url": "https://www.facebook.com/p/Lucy-Bar-100057188120549/"},
    {"name": "Dark Pub", "url": "https://www.facebook.com/p/Dark-Pub-Hotelik-Official-100063812942422/"},
    {"name": "Dworcowa Gorlice", "url": "https://www.facebook.com/dworcowagorlice/"}
]

# --- LOGOWANIE ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8'), logging.StreamHandler()]
)

def download_media(url, save_path, session_cookies):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"}
        jar = requests.cookies.RequestsCookieJar()
        for cookie in session_cookies:
            jar.set(cookie['name'], cookie['value'])
        
        r = requests.get(url, headers=headers, cookies=jar, timeout=20)
        if r.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(r.content)
            return True
    except Exception as e:
        logging.error(f"   [!] Błąd pobierania zdjęcia: {e}")
    return False

def slugify(text):
    """Tworzy bezpieczną nazwę folderu z nazwy restauracji."""
    return re.sub(r'[^a-zA-Z0-9]', '', text)

# --- KONFIGURACJA PRZEGLĄDARKI ---
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
options.add_argument("--width=1920")
options.add_argument("--height=1080")

driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)
final_data = []

try:
    # --- LOGOWANIE PRZEZ COOKIES ---
    logging.info("Wczytywanie ciasteczek...")
    driver.get("https://www.facebook.com")
    time.sleep(3)
    
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, 'r') as f:
            cookies = json.load(f)
            for cookie in cookies:
                if 'sameSite' in cookie and cookie['sameSite'] not in ["Strict", "Lax", "None"]:
                    del cookie['sameSite']
                try:
                    driver.add_cookie(cookie)
                except Exception:
                    pass
        logging.info("Ciasteczka załadowane. Odświeżam...")
        driver.refresh()
        time.sleep(5)
    else:
        logging.warning("Brak pliku cookies.json! Skrapowanie jako gość.")

    logging.info("### ROZPOCZĘCIE SKANOWANIA GASTRO ###")
    
    for rest in RESTAURANTS:
        display_name = rest["name"]
        url = rest["url"]
        folder_id = slugify(display_name)
        
        logging.info(f"Otwieram: {display_name}...")
        
        try:
            driver.get(url)
            time.sleep(7) 

            articles = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
            if not articles:
                logging.warning(f"   [!] Nie znaleziono postów dla {display_name}")
                continue
            
            first_post = articles[0]

            # Rozwijanie "Zobacz więcej"
            driver.execute_script("""
                let art = arguments[0];
                let moreBtns = Array.from(art.querySelectorAll('div[role="button"]'))
                    .filter(b => b.innerText && (b.innerText.toLowerCase().includes('więcej') || b.innerText.toLowerCase().includes('see more')));
                if (moreBtns.length > 0) {
                    moreBtns[0].click();
                }
            """, first_post)
            time.sleep(1.5)

            # Pobieranie treści i zdjęć przez JS
            post_data = driver.execute_script("""
                let art = arguments[0];
                const clean = (t) => t.replace(/\\n+/g, '\\n').trim();
                const trash = ["followers", "following", "recommend", "reviews", "privacy", "terms"];

                let textNodes = Array.from(art.querySelectorAll('div[dir="auto"]'))
                    .map(el => el.innerText)
                    .filter(t => t && t.length > 20 && !trash.some(word => t.toLowerCase().includes(word)));

                let content = [...new Set(textNodes)].join('\\n');

                let images = Array.from(art.querySelectorAll('img'))
                    .filter(i => i.src.includes('fbcdn') && i.width > 200) 
                    .map(i => i.src);

                let uniqueImages = [...new Set(images)];

                return (content.length > 2 || uniqueImages.length > 0) ? { content: clean(content), media: uniqueImages } : null;
            """, first_post)

            saved_images = []
            if post_data:
                # Obsługa mediów
                if post_data['media']:
                    path = os.path.join(MEDIA_DIR, folder_id)
                    os.makedirs(path, exist_ok=True)
                    
                    for idx, img_url in enumerate(post_data['media']):
                        img_filename = f"post1_img{idx+1}.jpg"
                        full_save_path = os.path.join(path, img_filename)
                        
                        if download_media(img_url, full_save_path, driver.get_cookies()):
                            saved_images.append(f"/gastro_media/{folder_id}/{img_filename}")
                
                # Dodawanie do listy końcowej
                final_data.append({
                    "restaurant_name": display_name,
                    "restaurant_url": url,
                    "posts": [
                        {
                            "content": post_data['content'],
                            "images": saved_images
                        }
                    ],
                    "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                logging.info(f"   [OK] Pobrano dane dla {display_name}")
            else:
                logging.warning(f"   [!] Brak wartościowej treści dla {display_name}")

        except Exception as e:
            logging.error(f"   [X] Błąd przy {display_name}: {e}")

finally:
    # Zapis finalnego JSONa
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    driver.quit()
    
    # Próba nadania uprawnień do folderów (opcjonalne)
    try:
        if os.name != 'nt': # Tylko na Linux/Mac
            os.system(f"chmod -R 755 {REACT_PUBLIC_DIR}")
    except:
        pass
        
    logging.info(f"### ZAKOŃCZONO. Dane zapisane w: {JSON_OUTPUT} ###")