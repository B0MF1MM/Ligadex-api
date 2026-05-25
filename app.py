import urllib.parse
import re
import requests

from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

# =========================================
# CACHE
# =========================================
cache_precos = {}

# =========================================
# EXTRAIR PREÇOS
# =========================================
def extrair_precos(texto):

    precos = re.findall(
        r"R\$\s*[\d\.]+,\d{2}",
        texto
    )

    if len(precos) >= 3:
        return {
            "menor": precos[0],
            "medio": precos[1],
            "maior": precos[2]
        }

    return None

# =========================================
# ROTA
# =========================================
@app.route('/api/preco', methods=['GET'])
def preco():
    nome_carta = request.args.get('carta')
    edicao = request.args.get('ed')
    numero = request.args.get('num')

    if not nome_carta:
        return jsonify({"erro": "Carta não enviada"}), 400

    cache_key = f"{nome_carta}-{edicao}-{numero}"

    if cache_key in cache_precos:
        print("CACHE:", nome_carta)
        return jsonify(cache_precos[cache_key])

    print("BUSCA NOVA:", nome_carta)

    try:
        nome_carta_link = urllib.parse.quote(nome_carta)

        url = (
            "https://www.ligapokemon.com.br/"
            f"?view=cards/card"
            f"&card={nome_carta_link}"
            f"&ed={edicao}"
            f"&num={numero}"
        )

        print("URL:", url)

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code != 200:
            return jsonify({"erro": "Falha ao acessar site"}), 500

        soup = BeautifulSoup(response.text, "html.parser")

        texto_pagina = soup.get_text()

        precos_finais = {}

        # NORMAL
        if "Normal" in texto_pagina:
            trecho = texto_pagina.split("Normal")[1][:1000]
            dados = extrair_precos(trecho)
            if dados:
                precos_finais["normal"] = dados

        # FOIL
        if "Foil" in texto_pagina:
            trecho = texto_pagina.split("Foil")[1][:1000]
            dados = extrair_precos(trecho)
            if dados:
                precos_finais["foil"] = dados

        # REVERSE FOIL
        if "Reverse Foil" in texto_pagina:
            trecho = texto_pagina.split("Reverse Foil")[1][:1000]
            dados = extrair_precos(trecho)
            if dados:
                precos_finais["reverse_foil"] = dados

        if not precos_finais:
            print("NENHUM PREÇO ENCONTRADO")

        cache_precos[cache_key] = precos_finais

        return jsonify(precos_finais)

    except Exception as e:
        print("ERRO:", str(e))
        return jsonify({"erro": str(e)}), 500


# =========================================
# START
# =========================================
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )