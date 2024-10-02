from selenium.webdriver import Firefox as Driver
from selenium.webdriver import FirefoxOptions as DriverOptions
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from datetime import datetime, timedelta
from base64 import b64encode
import bz2

# Número máximo de tentativas de carregar o site.
MAX_TRY = 5

# Nomes dos arquivos.
LINKS_FILE = "links_r7.txt"
PAGES_FILE = "pages_r7.txt"
LOGS_FILE = "logs_r7_pages.txt"

# Offset utilizado para que, caso o script seja interrompido, não seja necessário refazer todo o scraping. Ele fica registrado na última linha do arquivo de logs.
OFFSET = 0

def start_driver(options:DriverOptions):
    driver = Driver(options=options)
    driver.set_page_load_timeout(10)
    return driver

def create_options():
    options = DriverOptions()
    options.set_preference("javascript.enabled", False)
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-application-cache")
    options.browser_version = "128"
    options.page_load_strategy = "eager"
    return options

def wait(driver:Driver, seconds:float):
    t = datetime.now()
    WebDriverWait(driver, seconds+10).until(lambda d: datetime.now() - t > timedelta(seconds=seconds))

def log(file, text):
    print(text)
    file.write(text + "\n")

try:
    options = create_options()
    driver = start_driver(options)

    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        links = f.readlines()

    pages_f = open(PAGES_FILE, "a", encoding="utf-8")
    logs_f = open(LOGS_FILE, "a", encoding="utf-8")

    index = OFFSET
    last = ""
    for link in links:
        link = link[:-1]
        
        success = False
        for i in range(MAX_TRY):
            # Tenta carregar a página.
            try:
                driver.get(link)
            except (TimeoutException) as e:
                print(f"Try #{i+1}")
                continue
            # Espera para não sobrecarregar o site.
            wait(driver, 5)
            
            page = driver.page_source
            if page == last:
                print(f"Try #{i+1}")
                continue
            last = page

            # Comprime a página.
            page_compressed = bz2.compress(page.encode("utf-8"), 1)
            page64 = b64encode(page_compressed).decode("ascii")
            success = True
            break
        if not success:
            log(logs_f, f"Page scraping failed at {link}")
            page64 = ""
        # Salva a página comprimida.
        pages_f.write(f"{link}|{page64}\n")

        index += 1

except Exception as e:
    log(logs_f, repr(e))
    log(logs_f, f"Scraping stopped at link: {link}. OFFSET={index}")
finally:
    driver.close()
    pages_f.close()
    logs_f.close()