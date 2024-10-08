from selenium.webdriver import Firefox as Driver
from selenium.webdriver import FirefoxOptions as DriverOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from selenium.webdriver.support.wait import WebDriverWait
from bs4 import BeautifulSoup, ResultSet, Tag
from urllib.parse import urlparse, parse_qs, ParseResult
from datetime import date, timedelta, datetime

# Intervalo de busca.
BEGIN = date(2022, 8, 30)
END = date(2023, 1, 31)
# Devido ao g1 limitar os resultados de busca a até 40 páginas, é necessário subdividir o intervalo de busca. Essa subdivisão é dada pelo delta.
DELTA = timedelta(days=5)
# Alguns termos retornam muito mais resultados do que os demais e, portanto, tem um delta próprio.
DELTAS = {"STF": timedelta(days=2), "TSE": timedelta(days=2), "Alexandre de Moraes": timedelta(days=2)}

# Termos de busca.
QUERIES = ["STF", "TSE", "Alexandre de Moraes", "Carmen Lúcia", "Nunes Marques", "Benedito Gonçalves", "Raul Araújo",
        "Carlos Horbach", "Sérgio Banhos", "Rosa Weber", "Luís Roberto Barroso", "Gilmar Mendes", "Ricardo Lewandowski",
        "Toffoli", "Luiz Fux", "Edson Fachin", "André Mendonça"]

# Offset utilizado para que, caso o script seja interrompido, não seja necessário refazer todas as buscas. Ele fica registrado na última linha do arquivo de logs.
QUERY_OFFSET = 0

# O g1 divide os resultados de busca em quatro categorias: Notícias, Fotos, Vídeos e Blogs. Não incluímos Fotos e Vídeos pois só coletamos texto.
SPECIES = ["notícias", "blogs"]

# O g1 é extremamente abrangente na busca dos termos. O termo "Dias Toffoli", por exemplo, pode retornar qualquer resultado que contenha "dia".
# Porém os primeiros resultados tendem a ser os mais relevantes.
# Com isso em vista, o "strike limit" define quantos resultados irrelevantes seguidos o script vai tolerar antes de abandonar essa busca.
STRIKE_LIMIT = 5

# Nomes dos arquivos.
LINKS_FILE = "links_g1.txt"
LINKS_PARTIAL_FILE = "links_g1_partial.txt"
LOGS_FILE = "logs_g1_links.txt"

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
    options.page_load_strategy = "eager"
    return options

def wait(driver:Driver, seconds:float):
    t = datetime.now()
    WebDriverWait(driver, seconds+10).until(lambda d: datetime.now() - t > timedelta(seconds=seconds))

def log(file, text):
    print(text)
    file.write(text + "\n")

# Tenta carregar os links parciais. Se o arquivo não existir, começa do zero.
try:
    with open(LINKS_PARTIAL_FILE, "r", encoding="utf-8") as f:
        g1_links = set(f.readlines())
except FileNotFoundError:
    g1_links = set()


try:
    options = create_options()
    driver = start_driver(options)
    driver_wait = WebDriverWait(driver, timeout=15)

    links_f = open(LINKS_FILE, "w", encoding="utf-8")
    logs_f = open(LOGS_FILE, "a", encoding="utf-8")

    for query_index in range(QUERY_OFFSET, len(QUERIES)):
        query = QUERIES[query_index]
        begin = BEGIN
        delta = DELTAS.get(query, DELTA)
        end = begin + delta - timedelta(days=1)
        while begin <= END:
            if end > END:
                end = END
            for specie in SPECIES:
                strikes = 0
                for page in range(1, 42):
                    # Como o limite de resultados do g1 é de 40 páginas, caso a busca chegue na página 40, o script é interrompido.
                    # Caso isso aconteça, altere o valor de delta para este termo na constante "DELTAS".
                    if page > 40:
                        raise Exception(f"News overflow at query '{query}', date {begin}, specie '{specie}'")
                    
                    # Carrega a página.
                    driver.get(f"https://g1.globo.com/busca/?q={query}&page={page}&order=recent&from={begin}T00%3A00%3A00-0300&to={end}T23%3A59%3A59-0300&species={specie}")
                    driver_wait.until(presence_of_element_located((By.CLASS_NAME, "results__list")))
                    news_raw = driver.find_element(By.CLASS_NAME, "results__list")

                    news_parsed = BeautifulSoup(news_raw.get_attribute("innerHTML"), "html.parser")
                    driver.delete_all_cookies()

                    # Coleta os links encontrados na página.
                    links:ResultSet[Tag] = news_parsed.find_all(lambda tag: tag.name == "a" and "widget--info__text-container" in tag.parent["class"])
                    # links = [parse_qs(urlparse(tag.get("href")).query)["u"][0] + "\n" for tag in links_parsed]
                    if not links:
                        log(logs_f, f"No links at query '{query}', date {begin}, specie '{specie}', page {page}")
                        break
                    
                    # Verifica se a matéria realmente contém o termo de busca. Se contém, adiciona o link, senão adiciona um strike.
                    description:ResultSet[Tag] = [x.text for x in news_parsed.find_all(class_="widget--info__description")]
                    for link in links:
                        description = link.find(class_="widget--info__description").text
                        if description.find(query) == -1:
                            strikes += 1
                            # Caso o número de strikes consecutivos seja maior do que o limite, abandona esta busca.
                            if strikes > STRIKE_LIMIT:
                                log(logs_f, f"Strike limit reached at query '{query}', date {begin}, specie '{specie}', page {page}")
                                break
                        else:
                            url_parsed:ParseResult = urlparse(link.get("href"))
                            link_parsed = parse_qs(url_parsed.query)["u"][0] + "\n"
                            g1_links.add(link_parsed)
                            strikes = 0

                    # Espera para não sobrecarregar o site.
                    wait(driver, 2)
            
            # Atualização do intervalo de busca.
            begin += delta
            end += delta
    
    links_f.writelines(g1_links)
except Exception as e:
    log(logs_f, repr(e))
    log(logs_f, f"Scraping stopped at query '{query}', date {begin}, specie '{specie}', page {page}. QUERY_OFFSET={query_index}")
    with open(LINKS_PARTIAL_FILE, "w", encoding="utf-8") as f:
        f.writelines(g1_links)
finally:
    driver.quit()
    links_f.close()
    logs_f.close()