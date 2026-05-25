import urllib.parse
import re
import cloudscraper
from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

cache_precos = {}

# =========================
# CLOUDSCRAPER — bypassa proteção anti-bot/Cloudflare
# Substitui o requests.get comum que era bloqueado com 403
# =========================
scraper = cloudscraper.create_scraper(
    browser={
        "browser": "chrome",
        "platform": "windows",
        "mobile": False,
    }
)

# Headers extras para parecer ainda mais com um navegador real
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
    # Simula que o usuário veio de uma busca no Google
    "Referer": "https://www.google.com/",
}


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
# SCRAPING COM CLOUDSCRAPER
# =========================
def buscar_dados(url):
    try:
        r = scraper.get(url, headers=HEADERS, timeout=20)

        print(f"URL: {url}")
        print(f"STATUS: {r.status_code}")

        if r.status_code != 200:
            print(f"STATUS ERROR: {r.status_code}")
            return {}

        soup = BeautifulSoup(r.text, "html.parser")
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

        return resultados

    except Exception as e:
        print(f"ERRO SCRAPING: {e}")
        return {}


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

        if not dados:
            dados = {}  # Retorna vazio — front já trata isso como "sem preços"

        cache_precos[cache_key] = dados
        return jsonify(dados)

    except Exception as e:
        print(f"ERRO GERAL: {e}")
        return jsonify({"erro": True, "mensagem": str(e)}), 500


# =========================
# HEALTHCHECK (útil no Render)
# =========================
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "cache": len(cache_precos)}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)