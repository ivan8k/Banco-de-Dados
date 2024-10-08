from selenium.webdriver import Firefox as Driver
from selenium.webdriver import FirefoxOptions as DriverOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from bs4 import BeautifulSoup, ResultSet, Tag
from datetime import datetime, timedelta
import re

# Seção na qual o scraping será realizado.
SECTION = "brasil"
# SECTION = "economia"

# Intervalo de busca.
BEGIN = datetime(2015, 1, 1)
END = datetime(2018, 12, 31)

# O script também funciona começando da página 1, mas é recomendado selecionar uma página próxima do intervalo desejado para evitar acessos desnecessários ao site.
# Aqui já constam valores razoáveis para ambas as seções.
PAGE_START = {"brasil": 12000, "economia": 1000}

# Nomes dos arquivos.
LINKS_FILE = f"links_oantagonista_{SECTION}.txt"
LOGS_FILE = f"logs_oantagonista_links_{SECTION}.txt"

# Definição de funções.
def start_driver(options:DriverOptions):
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

    links_f = open(LINKS_FILE, "a")
    logs_f = open(LOGS_FILE, "a")


    page = PAGE_START[SECTION]
    last_links = []
    date = datetime(3000)
    while(date >= BEGIN):
        # Carrega a página.
        driver.get(f"https://oantagonista.com.br/{SECTION}/page/{page}")

        news_raw = driver.find_element(By.CLASS_NAME, "ultimas-noticias-area")

        news_parsed = BeautifulSoup(news_raw.get_attribute("innerHTML"), "html.parser")
        driver.delete_all_cookies()

        # Coleta a data da notícia mais antiga.
        dates:ResultSet[Tag] = news_parsed.find_all(class_="date-time__date")
        date_string = re.findall("[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{4}", dates[-1].text)[0]
        date = datetime.strptime(date_string, " %d.%m.%Y")
        # Ignora a página caso a data não esteja no intervalo.
        if date > END:
            page += 1
            continue
        
        # Coleta os links encontrados na página.
        news_links:ResultSet[Tag] = news_parsed.find_all("a")
        news_links_sorted = [news_links[0]] + [news_links[3]] + news_links[1:3] + news_links[4:11]

        links:list[str] = [tag.get("href") for tag in news_links_sorted]
        for link in links:
            if link not in last_links:
                links_f.write(f"{link}\n")
            else:
                log(logs_f, f"Duplicate found at page {page}")
        last_links = links.copy()

        # Espera para não sobrecarregar o site.
        wait(driver, 1)

        page += 1
except Exception as e:
    log(logs_f, repr(e))
finally:
    driver.quit()
    links_f.close()
    log(logs_f, f"Scraping stopped at page {page}")
    logs_f.close()