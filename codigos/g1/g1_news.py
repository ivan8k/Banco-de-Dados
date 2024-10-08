from bs4 import BeautifulSoup, Tag
from datetime import datetime
import re
from base64 import b64decode
import bz2

# Lista de links selecionados manualmente para serem ignorados.
SKIP_LIST = ["https://g1.globo.com/rr/roraima/eleicoes/2022/noticia/2022/08/29/ipec-27percent-nao-votariam-em-teresa-surita-para-governadora-de-roraima-24percent-rejeitam-antonio-denarium.ghtml"]

# Intervalo de busca.
BEGIN = datetime(2022, 8, 16)
END = datetime(2023, 1, 31)

# Termos de busca.
QUERIES = ["STF", "TSE", "Alexandre de Moraes", "Carmen Lúcia", "Nunes Marques", "Benedito Gonçalves", "Raul Araújo",
        "Carlos Horbach", "Sérgio Banhos", "Rosa Weber", "Luís Roberto Barroso", "Gilmar Mendes", "Ricardo Lewandowski",
        "Toffoli", "Luiz Fux", "Edson Fachin", "André Mendonça"]

# Offset utilizado para que, caso o script seja interrompido, não seja necessário refazer todo o processamento. Ele fica registrado na última linha do arquivo de logs.
OFFSET = 0

# Expressão regular usada para detectar e remover links de anúncio
AD_LINK = "<strong>[^<]*([:\?]\s*</strong>|</strong>\s*[:\?])\s*.{,5}<a[^>]*>[^<]*</a>\s*"

# Expressão regular usada para detectar e remover textos de anúncio
AD_TEXT = "^.? ?v[íi]deos?(: | mais)|^.? ?leia (tamb[ée]m|mais|outr)|^.? ?veja (mais|tamb[ée]m|outr|v[íi]deo)|^.? ?(compartilhe |clique |acesse |confira |acompanhe |assista |ouça |saiba mais)"

# Nomes dos arquivos.
PAGES_FILE = "pages_g1.txt"
DATA_FILE = "data_g1.csv"
LOGS_FILE = "logs_g1_data.txt"

# Definição de funções.
def log(file, text):
    print(text)
    file.write(text + "\n")

try:
    pages_f = open("PAGES_FILE", "r", encoding="utf-8")
    logs_f = open(LOGS_FILE, "a", encoding="utf-8")
    data_f = open(DATA_FILE, "a", encoding="utf-8")

    for i in range(OFFSET):
        pages_f.readline()
    
    index = OFFSET
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

        # Ignora links da categoria "especiais".
        if "especiais.g1.globo.com" in link:
            index += 1
            continue

        # Descomprime a página.
        page_compressed = b64decode(page64.encode("utf-8"))
        page = bz2.decompress(page_compressed).decode("utf-8")
        

        page_parsed = BeautifulSoup(page.replace("<br>", "\n").replace("<li>", "<li>\n"), "lxml")
        
        # Processa a página.
        article = page_parsed.find(class_="mc-body")

        title = article.find(itemprop="headline").text.strip().replace("\t", "").replace('"', '""')
        
        authors_aux = article.find(class_="content-publication-data__from")
        if authors_aux:
            authors = authors_aux["title"].replace("\t", "").replace('"', '""')
        
        date = re.findall("[0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.][0-9]{4}", article.find(itemprop="datePublished").text)[0].replace("-", "/").replace(".", "/")
        
        lead_aux = article.find(itemprop="alternativeHeadline")
        if lead_aux:
            lead = lead_aux.text.strip().replace("\t", "").replace('"', '""')
        
        article_body = article.find(itemprop="articleBody")
        
        for tag in article_body.find_all(id=re.compile("chunk-")):
            a = tag.find("a")
            if isinstance(a, Tag) and a.text.strip() == tag.text.strip():
                tag.decompose()
            elif re.search(AD_LINK, str(tag)):
                tag.decompose()
        
        body = "\n".join([x.text.strip() for x in article_body.find_all(class_="content-text") if not re.search(AD_TEXT, x.text.strip().lower())]).replace("\t", "").replace('"', '""')

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
        data_f.write(f'"{title}"\t"{authors}"\t"{date}"\t"{lead}"\t"{body}"\t"{link}"\n')

        index += 1

except Exception as e:
    log(logs_f, repr(e))
    log(logs_f, f"Scraping stopped at link: {link}. OFFSET: {index}")
finally:
    pages_f.close()
    data_f.close()
