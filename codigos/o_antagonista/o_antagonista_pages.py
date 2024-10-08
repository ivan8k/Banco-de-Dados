from selenium.webdriver import Firefox as Driver
from selenium.webdriver import FirefoxOptions as DriverOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import TimeoutException
from datetime import datetime, timedelta
from base64 import b64encode
import bz2

# Seção na qual o scraping será realizado.
SECTION = "brasil"
# SECTION = "economia"

# Offset utilizado para que, caso o script seja interrompido, não seja necessário refazer todo o scraping. Ele fica registrado na última linha do arquivo de logs.
OFFSET = 0

# Número máximo de tentativas de carregar o site.
MAX_TRY = 5

# Nomes dos arquivos.
LINKS_FILE = f"links_oantagonista_{SECTION}.txt"
PAGES_FILE = f"pages_oantagonista_{SECTION}.txt"
LOGS_FILE = f"logs_oantagonista_pages_{SECTION}.txt"

# Definição de funções.
def start_driver(options:DriverOptions, old_driver:Driver=None):
    # if old_driver:
    #     old_driver.quit()
    #     time.sleep(5)
    driver = Driver(options=options)
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
    driver_wait = WebDriverWait(driver, 30)

    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        links = f.readlines()[OFFSET:]

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
                driver_wait.until(presence_of_element_located((By.TAG_NAME, "article")))
            except (TimeoutException) as e:
                print(f"Try #{i+1}")
                continue
            # Espera para não sobrecarregar o site.
            wait(driver, 2)
            
            page = driver.page_source
            if page == last:
                print(f"Try #{i+1}")
                continue
            last = page

            # Comprime a página.
            page_compressed = bz2.compress(page.encode("utf-8"), 1)
            page64 = b64encode(page_compressed).decode("utf-8")
            success = True
            break
        if not success:
            log(logs_f, f"Page scraping failed at {link}")
            page64 = ""
        # Salva a página comprimida.
        pages_f.write(f"{link}|{page64}\n")

        index += 1
        # if index % 200 == 0:
        #     driver = start_driver(options, driver)

except Exception as e:
    log(logs_f, repr(e))
finally:
    driver.quit()
    log(logs_f, f"Scraping stopped at link {link}\n")
    logs_f.close()
