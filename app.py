import urllib.parse
import re
import time
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
import undetected_chromedriver as uc

app = Flask(__name__)
CORS(app)

cache_precos = {}


def criar_driver():
    opcoes = uc.ChromeOptions()
    opcoes.add_argument("--headless=new")
    opcoes.add_argument("--no-sandbox")
    opcoes.add_argument("--disable-dev-shm-usage")
    opcoes.add_argument("--disable-gpu")
    opcoes.add_argument("--window-size=1920,1080")

    chrome_bin = os.environ.get("CHROME_BIN")
    if chrome_bin:
        opcoes.binary_location = chrome_bin

    # ✅ version_main=148 garante que o driver baixado bata com o Chrome instalado
    driver = uc.Chrome(options=opcoes, use_subprocess=False, version_main=148)
    return driver


def extrair_precos(texto):
    precos = re.findall(r"R\$\s*[\d\.]+,\d{2}", texto)
    if len(precos) >= 3:
        return {
            "menor": precos[0],
            "medio": precos[1],
            "maior": precos[2],
        }
    return None


def buscar_dados(url):
    driver = None
    try:
        print(f"URL: {url}", flush=True)
        driver = criar_driver()
        driver.get(url)
        time.sleep(6)

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        texto = soup.get_text(" ")

        print(f"TAMANHO: {len(texto)}", flush=True)
        print(f"TRECHO: {texto[:500]}", flush=True)

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

        print(f"RESULTADO: {resultados}", flush=True)
        return resultados

    except Exception as e:
        print(f"ERRO: {e}", flush=True)
        return {}

    finally:
        if driver:
            driver.quit()


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
            print(f"CACHE HIT: {cache_key}", flush=True)
            return jsonify(cache_precos[cache_key])

        print(f"BUSCA NOVA: {nome}", flush=True)

        nome_enc = urllib.parse.quote(nome)
        url = (
            "https://www.ligapokemon.com.br/"
            f"?view=cards/card&card={nome_enc}&ed={ed}&num={num}"
        )

        dados = buscar_dados(url)
        cache_precos[cache_key] = dados
        return jsonify(dados)

    except Exception as e:
        print(f"ERRO GERAL: {e}", flush=True)
        return jsonify({"erro": True, "mensagem": str(e)}), 500


@app.route("/api/debug", methods=["GET"])
def debug():
    driver = None
    try:
        url = request.args.get(
            "url",
            "https://www.ligapokemon.com.br/?view=cards/card&card=Kakuna%20%28002%2F086%29&ed=CRI&num=002"
        )
        driver = criar_driver()
        driver.get(url)
        time.sleep(6)
        texto = BeautifulSoup(driver.page_source, "html.parser").get_text(" ")
        return jsonify({
            "url": url,
            "tamanho": len(texto),
            "trecho": texto[:3000],
        })
    except Exception as e:
        return jsonify({"erro": str(e)})
    finally:
        if driver:
            driver.quit()


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "cache": len(cache_precos)}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)