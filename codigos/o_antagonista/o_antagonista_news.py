from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from base64 import b64decode
import bz2

# Seção na qual o scraping será realizado.
SECTION = "brasil"
# SECTION = "economia"

# Lista de links selecionados manualmente para serem ignorados.
SKIP_LIST = []

# Intervalo de busca.
BEGIN = datetime(2015, 1, 1)
END = datetime(2018, 12, 31) + timedelta(days=1)

# Offset utilizado para que, caso o script seja interrompido, não seja necessário refazer todo o processamento. Ele fica registrado na última linha do arquivo de logs.
OFFSET = 0

# Nomes dos arquivos.
PAGES_FILE = f"pages_oantagonista_{SECTION}.txt"
DATA_FILE = f"data_oantagonista_{SECTION}.csv"
LOGS_FILE = f"logs_oantagonista_pages_{SECTION}.txt"

# Definição de funções.
def log(file, text):
    print(text)
    file.write(text + "\n")

try:
    pages_f = open(PAGES_FILE, "r", encoding="utf-8")
    logs_f = open(LOGS_FILE, "a", encoding="utf-8")
    data_f = open(DATA_FILE, "a", encoding="utf-8")

    for i in range(OFFSET):
        pages_f.readline()
    
    index = 0
    while True:
        # Carrega uma página comprimida.
        line = pages_f.readline()
        if not line:
            break
        link, page64 = line[:-1].split("|")

        # Ignora links da lista "SKIP_LIST".
        if link in SKIP_LIST:
            index += 1
            continue

        # Descomprime a página.
        page_compressed = b64decode(page64.encode("utf-8"))
        page = bz2.decompress(page_compressed).decode("utf-8")

        # Processa a página.
        page_parsed = BeautifulSoup(page.replace("<br>", "\n").replace("<li>", "<li>\n"), "lxml")

        article = page_parsed.find("article")

        title = article.find("h1").text.strip().replace("\t", "").replace('"', '""')
        authors = ", ".join(map(lambda x: x.text, article.find_all(class_="post-interna__autor__pessoa__nome"))).replace("\t", "").replace('"', '""')
        date = list(article.find_all(class_="post-interna__autor__item")[1].strings)[1].strip().replace('"', '""')
        body = "\n".join(map(lambda x: x.text, article.find(class_="post-interna__content__corpo").find_all("p"))).replace("\t", "").replace('"', '""')
        
        # Verifica se a data da matéria está dentro do intervalo dado. Caso não esteja, ignora esta página.
        date_parsed = datetime.strptime(date, "%d.%m.%Y %H:%M")
        if date_parsed < BEGIN or date_parsed > END:
            index += 1
            continue

        data_f.write(f'"{title}"\t"{authors}"\t"{date}"\t"{body}"\n')

        index += 1

except Exception as e:
    log(logs_f, repr(e))
    log(logs_f, f"Scraping stopped at link: {link}. OFFSET: {index}")
finally:
    pages_f.close()
    data_f.close()
    logs_f.close()