from selenium.webdriver import Firefox as Driver
from selenium.webdriver import FirefoxOptions as DriverOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from os import getcwd
from pathlib import Path
import re

# Lista de links raiz de cada ex-presidente.
ROOT_LINKS = ("http://www.biblioteca.presidencia.gov.br/presidencia/ex-presidentes/bolsonaro/Bolsonaro",
        "http://www.biblioteca.presidencia.gov.br/presidencia/ex-presidentes/michel-temer/michel_temer",
        "http://www.biblioteca.presidencia.gov.br/presidencia/ex-presidentes/dilma-rousseff",
        "http://www.biblioteca.presidencia.gov.br/presidencia/ex-presidentes/luiz-inacio-lula-da-silva",
        "http://www.biblioteca.presidencia.gov.br/presidencia/ex-presidentes/fernando-henrique-cardoso",
        "http://www.biblioteca.presidencia.gov.br/presidencia/ex-presidentes/itamar-franco",
        "http://www.biblioteca.presidencia.gov.br/presidencia/ex-presidentes/fernando-collor",
        "http://www.biblioteca.presidencia.gov.br/presidencia/ex-presidentes/jose-sarney")

# Tipo a ser raspado. Também é o nome da pasta onde os arquivos baixados serão armazenados.
TYPE = "mensagens"
# TYPE = "discursos"

# Título como está escrito no site.
TYPE_TITLE = {"mensagens": "Mensagens Presidenciais", "discursos": "Discursos Presidenciais"}

# Nomes dos arquivos.
DATA_FILE = f"data_expresidentes_{TYPE}.txt"
LOGS_FILE = f"logs_expresidentes_{TYPE}.txt"

def get_name(link:str):
    return link.split("/")[5]

def validate_link(link:str, name:str):
    if link.startswith("http") and name in link:
        link_fix = link.rpartition("/view")
        link = link if link_fix[2] else link_fix[0]
        return link
    return None

def wait(driver:Driver, seconds:float):
    t = datetime.now()
    WebDriverWait(driver, seconds+10).until(lambda d: datetime.now() - t > timedelta(seconds=seconds))

def create_options(name:str) -> DriverOptions:
    options = DriverOptions()
    options.page_load_strategy = 'none'
    options.browser_version = "128"

    options.set_preference("browser.download.dir", f"{getcwd()}\\{TYPE}\\{name}")
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")
    options.set_preference("browser.download.panel.shown", False)
    options.set_preference("browser.download.manager.showWhenStarting", False)
    options.set_preference("browser.download.manager.focusWhenStarting", False)
    options.set_preference("browser.download.useDownloadDir", True)
    options.set_preference("browser.helperApps.alwaysAsk.force", False)
    options.set_preference("browser.download.manager.closeWhenDone", True)
    options.set_preference("browser.download.manager.showAlertOnComplete", True)
    options.set_preference("browser.download.manager.useWindow", False)
    options.set_preference("services.sync.prefs.sync.browser.download.manager.showWhenStarting", False)
    options.set_preference("pdfjs.disabled", True)
    return options

def purge_drivers(drivers:list[tuple[Driver, str]]) -> bool:
    for driver, name in drivers[:]:
        if not list(Path(f"{getcwd()}\\{TYPE}\\{name}").glob("*.part")):
            driver.quit()
            drivers.remove((driver, name))

def log(file, text):
    print(text)
    file.write(text + "\n")

try:
    data_f = open(DATA_FILE, "a", encoding="utf-8")
    logs_f = open(LOGS_FILE, "a", encoding="utf-8")
    
    drivers = []
    for root_link in ROOT_LINKS:
        # Busca pelos links no site raiz.
        name = get_name(root_link)
        driver = Driver(options=create_options(name))
        while True:
            driver.get(root_link)
            try:
                WebDriverWait(driver, timeout=60).until(presence_of_element_located((By.ID, "content")))
                wait(driver, 5)
                break
            except TimeoutException as e:
                # Diversas vezes durante os testes o servidor do site ficou indisponível. Essas interrupções normalmente duram entre alguns minutos a uma hora.
                if driver.page_source.find("503") != -1:
                    print("Server Down. Retrying in 5 minutes.")
                    wait(driver, 300)
                else:
                    raise(e)
        content_raw = driver.find_element(By.ID, "content")
        content = BeautifulSoup(content_raw.get_attribute("innerHTML"), "lxml")
        title_list = content.find_all(class_="outstanding-title")

        sub_links:list[str] = []
        for title in title_list:
            if title.text == TYPE_TITLE[TYPE]:
                for link in title.find_next(class_="tile-content").find_all("a"):
                    link_val = validate_link(link.get("href"), name)
                    if link_val and link_val not in sub_links:
                        sub_links.append(link_val)
                break

        # Busca recursivamente pelas páginas/links de download
        visited = []
        i = 1
        while sub_links:
            sub_link = sub_links.pop(0)
            visited.append(sub_link)
            driver.get("about:blank")
            wait(driver, 1)
            driver.get(sub_link)
            try:
                if not sub_link.endswith(".pdf"):
                    WebDriverWait(driver, timeout=10).until(presence_of_element_located((By.ID, "content")))
                    wait(driver, 5)
                else:
                    wait(driver, 5)
                    continue
            except TimeoutException:
                # Diversas vezes durante os testes o servidor do site ficou indisponível. Essas interrupções normalmente duram entre alguns minutos a uma hora.
                if driver.page_source.find("503 Service Unavailable") != -1:
                    sub_links.insert(0, sub_link)
                    print("Server Down. Retrying in 5 minutes.")
                    wait(driver, 300)
                continue

            # Ignora links que redirecionam para outra página.
            if "?came_from=" in driver.current_url:
                continue

            # Verfica se a página possui mais links ou o conteúdo em si. 
            content = BeautifulSoup(driver.find_element(By.ID, "content").get_attribute("innerHTML").replace("<br>", "\n"), "html.parser")
            if content.find("article"):
                for link in content.find_all(class_="url"):
                    link_val = validate_link(link.get("href"), name)
                    if link_val and link_val not in visited and link_val not in sub_links:
                        sub_links.insert(0, link_val)
                for link in content.find_all(class_="proximo"):
                    link_val = validate_link(link.get("href"), name)
                    if link_val and link_val not in visited and link_val not in sub_links:
                        sub_links.insert(0, link_val)
            elif content.find("p"):
                title = content.find(class_="documentFirstHeading").text.replace("\t", "").replace('"', '""')
                body = content.find(id="parent-fieldname-text").text.replace("\t", "").replace('"', '""')
                text = f'{title}\n{body}'

                # Normalmente ou a data se encontra no título ou no começo do texto, porém vários exemplos sem data foram encontrados.
                # Ainda assim, talvez hajam textos que contenham a data de outras formas.
                date_txt = body[:100].replace(",", "")
                while date_txt.find("  ") != -1:
                    date_txt = date_txt.replace("  ", " ")
                re_match = re.search("[0-9]{1,2} de [a-zA-ZçÇ]* de [0-9]{4}", date_txt)
                if re_match:
                    p0, p1 = re_match.span()
                    date = date_txt[p0:p1]
                else:
                    re_match = re.search("[0-3]?[0-9]-[0-1]?[0-9]-[1-2][0-9]{3}", title)
                    if re_match:
                        p0, p1 = re_match.span()
                        date = title[p0:p1]
                    else:
                        date = ""
                        logs_f.write(f'No date found at line: {i}. Link: {sub_link}\n')
                data_f.write(f'"{date}"\t"{name}"\t"{text}"\t"{TYPE}"\n')
                i += 1
            elif content.find(class_="internal-link"):
                for link in content.find_all(class_="internal-link"):
                    link_val = validate_link(link.get("href"), name)
                    if link_val and link_val not in visited and link_val not in sub_links:
                        sub_links.insert(0, link_val)
                for link in content.find_all(class_="proximo"):
                    link_val = validate_link(link.get("href"), name)
                    if link_val and link_val not in visited and link_val not in sub_links:
                        sub_links.insert(0, link_val)
            else:
                log(logs_f, f"Unable to process link: {sub_link}")
        
        purge_drivers(drivers)
        drivers.append((driver, name))
    
except Exception as e:
    log(logs_f, repr(e))
finally:
    while drivers:
        wait(drivers[-1][0], 30)
        purge_drivers(drivers)
    logs_f.close()
    data_f.close()
    print(f"Link: {sub_link}")
