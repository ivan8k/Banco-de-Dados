from selenium.webdriver import Firefox as Driver
from selenium.webdriver import FirefoxOptions as DriverOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from selenium.webdriver.support.wait import WebDriverWait
from datetime import date, datetime, timedelta

# ATENÇÃO: Este script é semi-automático. Ele requer intervenções pontuais do usuário para preencher os CAPTCHAs do google.

# Intervalo de busca.
BEGIN = date(2022, 8, 16)
END = date(2023, 1, 31)
# Devido ao google limitar os resultados de busca a até 30 páginas, é necessário subdividir o intervalo de busca. Essa subdivisão é dada pelo delta.
# Neste caso específico, o google não retorna muitos resultados relevantes, e, portanto, a subdivisão foi considerada desnecessária.
# Por esse motivo, atualmente o delta compreende todo o intervalo, mas caso ache-se necessário, é possível diminuí-lo.
DELTA = timedelta(days=300)
# Alguns termos retornam muito mais resultados do que os demais e, portanto, tem um delta próprio.
DELTAS = {}

# Termos de busca.
QUERIES = ["STF", "TSE", "Alexandre de Moraes", "Carmen Lúcia", "Nunes Marques", "Benedito Gonçalves", "Raul Araújo",
        "Carlos Horbach", "Sérgio Banhos", "Rosa Weber", "Luís Roberto Barroso", "Gilmar Mendes", "Ricardo Lewandowski",
        "Toffoli", "Luiz Fux", "Edson Fachin", "André Mendonça"]

# Tempo que o script irá aguardar o usuário preencher o CAPTCHA (em segundos).
TIMEOUT = 600

# Nomes dos arquivos.
LINKS_FILE = "links_r7.txt"
LOGS_FILE = "logs_r7_links.txt"

def start_driver(options:DriverOptions):
    driver = Driver(options=options)
    return driver

def create_options():
    options = DriverOptions()
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

# Tenta carregar os links. Se o arquivo não existir, começa do zero.
try:
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        links = f.readlines()
except:
    links:list[str] = []

try:
    options = create_options()
    driver = Driver(options)
    driver_wait = WebDriverWait(driver, timeout=TIMEOUT)

    links_f = open(LINKS_FILE, "w", encoding="utf-8")
    logs_f = open(LOGS_FILE, "a", encoding="utf-8")

    for query in QUERIES:
        begin = BEGIN
        delta = DELTAS.get(query, DELTA)
        while begin < END:
            end = begin + delta - timedelta(days=1)
            if end > END:
                end = END
            
            # Carrega a página do google e inicia a busca.
            driver.get("https://google.com")
            driver.find_element(By.NAME, "q").send_keys(f'site:noticias.r7.com after:{begin} before:{end} intext:"{query}"{Keys.ENTER}')
            # Espera para não sobrecarregar o site.
            wait(driver, 3)

            # Detecta e aguarda o preenchimento de CAPTCHAs.
            if "Our systems have detected unusual traffic from your computer network" in driver.page_source:
                driver_wait.until(presence_of_element_located((By.ID, "rso")))
                # Espera para não sobrecarregar o site.
                wait(driver, 3)
            
            # Obtém os links das 30 páginas de resultado do google.
            for i in range(30):
                rso = driver.find_element(By.ID, "rso")
                for link_tag in rso.find_elements(By.TAG_NAME, "a"):
                    link = link_tag.get_property("href")
                    if link not in links and not link.startswith("https://www.google.com/search"):
                        links.append(link + "\n")
                try:
                    driver.find_element(By.ID, "pnnext").click()
                except:
                    break
                # Espera para não sobrecarregar o site.
                wait(driver, 3)

                # Detecta e aguarda o preenchimento de CAPTCHAs.
                if "Our systems have detected unusual traffic from your computer network" in driver.page_source:
                    driver_wait.until(presence_of_element_located((By.ID, "rso")))
                # Espera para não sobrecarregar o site.
                wait(driver, 3)

            # Atualização do intervalo de busca.
            begin += delta
            end += delta
except Exception as e:
    log(logs_f, f"Scraping stopped at query '{query}' in {begin}")
    log(logs_f, repr(e))
finally:
    # Salva os links.
    links_f.writelines(links)
    driver.quit()
    links_f.close()
    logs_f.close()