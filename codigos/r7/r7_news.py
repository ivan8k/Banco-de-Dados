from bs4 import BeautifulSoup, Tag
from datetime import datetime
from functools import reduce
from base64 import b64decode
import re
import bz2

# Lista de links selecionados manualmente para serem ignorados.
SKIP_LIST = ["https://noticias.r7.com/brasil/eleicoes-2022/", "https://noticias.r7.com/eleicoes-2022/"]

# Intervalo de busca.
BEGIN = datetime(2022, 8, 16)
END = datetime(2023, 1, 31)

# Termos de busca.
QUERIES = ["STF", "TSE", "Alexandre de Moraes", "Carmen Lúcia", "Nunes Marques", "Benedito Gonçalves", "Raul Araújo",
        "Carlos Horbach", "Sérgio Banhos", "Rosa Weber", "Luís Roberto Barroso", "Gilmar Mendes", "Ricardo Lewandowski",
        "Toffoli", "Luiz Fux", "Edson Fachin", "André Mendonça"]

# Offset utilizado para que, caso o script seja interrompido, não seja necessário refazer todo o processamento. Ele fica registrado na última linha do arquivo de logs.
OFFSET = 0

# Nomes dos arquivos.
PAGES_FILE = "pages_r7.txt"
DATA_FILE = "data_r7.csv"
LOGS_FILE = "logs_r7_data.txt"

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

        # Ignora links das categorias "integras" e "fotos".
        if re.search("/integras/|/fotos/", link):
            index += 1
            continue

        # Descomprime a página.
        page_compressed = b64decode(page64.encode("utf-8"))
        page = bz2.decompress(page_compressed).decode("utf-8")
        page = b64decode(page64.encode("ascii")).decode("utf-8")

        # Processa a página.
        page_parsed = BeautifulSoup(page.replace("<br>", "\n").replace("<li>", "<li>\n"), "lxml")

        article = page_parsed.find(class_="b-article-body")
        header = article.find("header")

        title = header.find("h1").text.strip().replace("\t", "").replace('"', '""')

        lead = header.find("h2").text.strip().replace("\n", "").replace("\t", "").replace('"', '""')

        author = re.sub(", em .*", "", header.find(class_=re.compile("article-text")).text.split("|")[1]).strip().replace("\t", "").replace('"', '""')

        date = re.findall("[0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.][0-9]{4}", header.find("time").text)[0].replace("-", "/").replace(".", "/")

        header.decompose()
        for tag in article.find_all(name=["figure"]):
            tag.decompose()
        for tag in list(article.children):
            aux:Tag = tag.find("a")
            if aux and aux.text.strip() == tag.text.strip():
                tag.decompose()
            elif tag.name == "div":
                tag.decompose()
            elif re.fullmatch("(leia|veja) (mais|também):?", tag.text.strip().lower()):
                tag.decompose()
            elif re.search("\s*(•|(leia|veja) (mais|também):)\s*<a.*?</a>\s*", str(tag).lower()):
                tag.decompose()
            else:
                tag.string = re.sub("\n+", " ", reduce(lambda a, b: f"{a}\n{b.lstrip()}", tag.text.splitlines(), "")).strip() + "\n"
        
        body = article.text.strip()
        body = body.replace("\t", "").replace('"', '""')

        # Verifica se o texto contém algum dos termos de busca. Caso não contenha, ignora esta página.
        success = False
        for query in QUERIES:
            if query in title or query in lead or query in body:
                success = True
                break
        if not success:
            index += 1
            continue
        
        # Verifica se a data da matéria está dentro do intervalo dado. Caso não esteja, ignora esta página.
        date_parsed = datetime.strptime(date, "%d/%m/%Y")
        if date_parsed < BEGIN or date_parsed > END:
            index += 1
            continue
        
        # Salva os dados.
        data_f.write(f'"{title}"\t"{author}"\t"{date}"\t"{lead}"\t"{body}"\n')

        index += 1

except Exception as e:
    log(logs_f, repr(e))
    log(logs_f, f"Scraping stopped at link: {link}. OFFSET: {index}")
finally:
    pages_f.close()
    data_f.close()
    logs_f.close()