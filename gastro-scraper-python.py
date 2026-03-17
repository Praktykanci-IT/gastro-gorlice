import json
import time
import os
import requests
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

# --- KONFIGURACJA ŚCIEŻEK (Zgodna z Twoją strukturą) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Ścieżka do folderu public w projekcie React
REACT_PUBLIC_DIR = os.path.join(BASE_DIR, "react", "gastro-gorlice", "public")

# Nowe lokalizacje plików wewnątrz folderu public
MEDIA_DIR = os.path.join(REACT_PUBLIC_DIR, "gastro_media") 
JSON_OUTPUT = os.path.join(REACT_PUBLIC_DIR, "gastro_data.json")

# Logi i ciasteczka zostają w folderze głównym skryptu
LOG_FILE = os.path.join(BASE_DIR, "scraper.log")
COOKIES_FILE = os.path.join(BASE_DIR, "cookies.json") 

# Tworzenie folderu na zdjęcia, jeśli nie istnieje
os.makedirs(MEDIA_DIR, exist_ok=True)

# --- LOGOWANIE DO PLIKU I KONSOLI ---
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

# --- KONFIGURACJA PRZEGLĄDARKI ---
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
options.add_argument("--width=1920")
options.add_argument("--height=1080")

driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)
final_data = []

urls = [
    "https://www.facebook.com/p/Pizzeria-Del-Piero-100063622118097/",
    "https://www.facebook.com/p/KEBAP-Stambu%C5%82-new-100057644341776/",
    "https://www.facebook.com/podzamczegorlice/",
    "https://www.facebook.com/803975942806402/",
    "https://www.facebook.com/PubPizzeriaChili/",
    "https://www.facebook.com/bilard.kregle/",
    "https://www.facebook.com/barnewyorkgorlice/",
    "https://www.facebook.com/p/Bar-mleczny-Wojtek-Gorlice-100063715833727/",
    "https://www.facebook.com/p/Lucy-Bar-100057188120549/",
    "https://www.facebook.com/p/Dark-Pub-Hotelik-Official-100063812942422/",
    "https://www.facebook.com/dworcowagorlice/"
]

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
        logging.info("Ciasteczka załadowane. Odświeżam stronę...")
        driver.refresh()
        time.sleep(5)
    else:
        logging.warning(f"UWAGA: Brak pliku {COOKIES_FILE}! Skrapowanie jako gość.")

    logging.info("### ROZPOCZĘCIE SKANOWANIA GASTRO ###")
    
    for url in urls:
        rest_name = url.rstrip("/").split("/")[-1]
        logging.info(f"Otwieram: {url}")
        
        try:
            driver.get(url)
            time.sleep(8) 

            articles = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
            if not articles:
                logging.warning(f"   [!] Nie znaleziono żadnych postów dla {rest_name}")
                continue
            
            first_post = articles[0]

            # Rozwijanie tekstu "Zobacz więcej"
            driver.execute_script("""
                let art = arguments[0];
                let moreBtns = Array.from(art.querySelectorAll('div[role="button"]'))
                    .filter(b => b.innerText && (b.innerText.toLowerCase().includes('więcej') || b.innerText.toLowerCase().includes('see more')));
                if (moreBtns.length > 0) {
                    moreBtns[0].click();
                }
            """, first_post)
            
            time.sleep(1.5)

            # Pobieranie danych z JS
            post_data = driver.execute_script("""
                let art = arguments[0];
                const clean = (t) => t.replace(/\\n+/g, '\\n').trim();
                const trash = ["followers", "following", "recommend", "reviews", "privacy", "terms"];

                let textNodes = Array.from(art.querySelectorAll('div[dir="auto"]'))
                    .map(el => el.innerText)
                    .filter(t => t && t.length > 20 && !trash.some(word => t.toLowerCase().includes(word)));

                let content = [...new Set(textNodes)].join('\\n');

                let images = Array.from(art.querySelectorAll('img'))
                    .filter(i => i.src.includes('fbcdn') && i.width > 150) 
                    .map(i => i.src);

                let uniqueImages = [...new Set(images)];

                return (content.length > 5 || uniqueImages.length > 0) ? { content: clean(content), media: uniqueImages } : null;
            """, first_post)

            posts = []
            if post_data:
                saved_images = []
                if post_data['media']:
                    path = os.path.join(MEDIA_DIR, rest_name)
                    os.makedirs(path, exist_ok=True)
                    
                    for idx, img_url in enumerate(post_data['media']):
                        img_filename = f"post1_img{idx+1}.jpg"
                        full_save_path = os.path.join(path, img_filename)
                        
                        if download_media(img_url, full_save_path, driver.get_cookies()):
                            # Ścieżka relatywna dla Reacta (z folderu public)
                            saved_images.append(f"/gastro_media/{rest_name}/{img_filename}")
                
                posts.append({"content": post_data['content'], "images": saved_images})
                logging.info(f"   [OK] Pobrano pierwszy post dla {rest_name} (zdjęć: {len(saved_images)})")
            else:
                logging.warning(f"   [!] Pierwszy post na {rest_name} okazał się pusty")

            final_data.append({
                "restaurant_name": rest_name, 
                "restaurant_url": url, 
                "posts": posts,
                "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

        except Exception as e:
            logging.error(f"   [X] Błąd przy {rest_name}: {e}")

finally:
    # Zapis JSON do public/gastro_data.json
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    driver.quit()
    
    # Próba nadania uprawnień (jeśli system na to pozwala)
    try:
        os.system(f"chmod -R 755 {REACT_PUBLIC_DIR}")
    except:
        pass
        
    logging.info(f"### ZAKOŃCZONO SESJĘ. Plik zapisany w: {JSON_OUTPUT} ###")