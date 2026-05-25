import urllib.parse
import re
import time
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

app = Flask(__name__)
CORS(app)

cache_precos = {}


# =========================
# CRIA DRIVER CHROME HEADLESS
# Usa Chrome do sistema (Render) ou ChromeDriver local
# =========================
def criar_driver():
    opcoes = Options()
    opcoes.add_argument("--headless=new")
    opcoes.add_argument("--no-sandbox")
    opcoes.add_argument("--disable-dev-shm-usage")
    opcoes.add_argument("--disable-gpu")
    opcoes.add_argument("--window-size=1920,1080")
    opcoes.add_argument("--disable-blink-features=AutomationControlled")
    opcoes.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    opcoes.add_experimental_option("excludeSwitches", ["enable-automation"])
    opcoes.add_experimental_option("useAutomationExtension", False)

    # Se estiver no Render/Linux, usa o chromium do sistema
    chrome_bin = os.environ.get("CHROME_BIN")
    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")

    if chrome_bin:
        opcoes.binary_location = chrome_bin

    if chromedriver_path:
        service = Service(executable_path=chromedriver_path)
    else:
        # Ambiente local — usa webdriver_manager
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=opcoes)

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return driver


# =========================
# EXTRATOR DE PREÇOS
# =========================
def extrair_precos(texto):
    precos = re.findall(r"R\$\s*[\d\.]+,\d{2}", texto)
    if len(precos) >= 3:
        return {
            "menor": precos[0],
            "medio": precos[1],
            "maior": precos[2],
        }
    return None


# =========================
# SCRAPING COM SELENIUM
# =========================
def buscar_dados(url):
    driver = None
    try:
        print(f"URL: {url}")
        driver = criar_driver()
        driver.get(url)

        time.sleep(3)  # Aguarda JS carregar a página

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        texto = soup.get_text(" ")

        resultados = {}
        blocos = {
            "normal": "Normal",
            "foil": "Foil",
            "reverse_foil": "Reverse Foil",
        }

        for key, label in blocos.items():
            if label in texto:
                try:
                    trecho = texto.split(label)[1][:1500]
                    dados = extrair_precos(trecho)
                    if dados:
                        resultados[key] = dados
                except Exception:
                    pass

        print(f"RESULTADO: {resultados}")
        return resultados

    except Exception as e:
        print(f"ERRO SELENIUM: {e}")
        return {}

    finally:
        if driver:
            driver.quit()


# =========================
# API
# =========================
@app.route("/api/preco", methods=["GET"])
def preco():
    try:
        nome = request.args.get("carta")
        ed = request.args.get("ed")
        num = request.args.get("num")

        if not nome:
            return jsonify({"erro": "carta ausente"}), 400

        cache_key = f"{nome}-{ed}-{num}"

        if cache_key in cache_precos:
            print(f"CACHE HIT: {cache_key}")
            return jsonify(cache_precos[cache_key])

        print(f"BUSCA NOVA: {nome}")

        nome_enc = urllib.parse.quote(nome)
        url = (
            "https://www.ligapokemon.com.br/"
            f"?view=cards/card&card={nome_enc}&ed={ed}&num={num}"
        )

        dados = buscar_dados(url)
        cache_precos[cache_key] = dados
        return jsonify(dados)

    except Exception as e:
        print(f"ERRO GERAL: {e}")
        return jsonify({"erro": True, "mensagem": str(e)}), 500


# =========================
# HEALTHCHECK
# =========================
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "cache": len(cache_precos)}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)