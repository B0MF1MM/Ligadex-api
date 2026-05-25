import urllib.parse
import re
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

cache_precos = {}

# =========================
# EXTRATOR ROBUSTO
# =========================
def extrair_precos(texto):
    precos = re.findall(r"R\$\s*[\d\.]+,\d{2}", texto)

    if len(precos) >= 3:
        return {
            "menor": precos[0],
            "medio": precos[1],
            "maior": precos[2]
        }

    return None


# =========================
# FUNÇÃO SEGURA DE SCRAPING
# =========================
def buscar_dados(url):

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )
    }

    try:
        r = requests.get(url, headers=headers, timeout=15)

        if r.status_code != 200:
            print("STATUS ERROR:", r.status_code)
            return {}

        soup = BeautifulSoup(r.text, "html.parser")

        texto = soup.get_text(separator=" ")

        # DEBUG REAL (IMPORTANTE)
        print("TEXTO PARCIAL:", texto[:1000])

        resultados = {}

        blocos = {
            "normal": "Normal",
            "foil": "Foil",
            "reverse_foil": "Reverse Foil"
        }

        for key, label in blocos.items():

            if label in texto:
                try:
                    trecho = texto.split(label)[1][:1500]
                    dados = extrair_precos(trecho)

                    if dados:
                        resultados[key] = dados

                except Exception as e:
                    print(f"Erro bloco {key}:", e)

        return resultados

    except Exception as e:
        print("ERRO REQUEST:", e)
        return {}


# =========================
# API
# =========================
@app.route('/api/preco', methods=['GET'])
def preco():

    try:
        nome = request.args.get('carta')
        ed = request.args.get('ed')
        num = request.args.get('num')

        if not nome:
            return jsonify({"erro": "carta ausente"}), 400

        cache_key = f"{nome}-{ed}-{num}"

        if cache_key in cache_precos:
            return jsonify(cache_precos[cache_key])

        print("BUSCA NOVA:", nome)

        nome_enc = urllib.parse.quote(nome)

        url = (
            "https://www.ligapokemon.com.br/"
            f"?view=cards/card&card={nome_enc}&ed={ed}&num={num}"
        )

        print("URL:", url)

        dados = buscar_dados(url)

        # 🔥 GARANTE QUE NUNCA QUEBRA API
        if not dados:
            dados = {
                "erro": False,
                "mensagem": "sem dados encontrados",
                "normal": None,
                "foil": None,
                "reverse_foil": None
            }

        cache_precos[cache_key] = dados

        return jsonify(dados)

    except Exception as e:
        print("ERRO GERAL:", str(e))

        return jsonify({
            "erro": True,
            "mensagem": str(e)
        }), 500


# =========================
# START
# =========================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)