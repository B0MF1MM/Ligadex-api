import time
import urllib.parse
import re

from flask import Flask, request, jsonify
from flask_cors import CORS

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By

from webdriver_manager.microsoft import EdgeChromiumDriverManager

app = Flask(__name__)
CORS(app)

# =========================================
# CACHE
# =========================================
cache_precos = {}

# =========================================
# NAVEGADOR
# =========================================
def iniciar_navegador():

    options = webdriver.EdgeOptions()

    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(
        EdgeChromiumDriverManager().install()
    )

    driver = webdriver.Edge(
        service=service,
        options=options
    )

    return driver

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
# API
# =========================================
@app.route('/api/preco', methods=['GET'])
def preco():
    return buscar_preco()

def buscar_preco():

    nome_carta = request.args.get('carta')
    edicao = request.args.get('ed')
    numero = request.args.get('num')

    # =====================================
    # VALIDAÇÃO
    # =====================================
    if not nome_carta:
        return jsonify({
            "erro": "Carta não enviada"
        }), 400

    # =====================================
    # CACHE
    # =====================================
    cache_key = f"{nome_carta}-{edicao}-{numero}"

    if cache_key in cache_precos:
        print(f"CACHE: {nome_carta}")
        return jsonify(cache_precos[cache_key])

    print(f"BUSCA NOVA: {nome_carta}")

    navegador = iniciar_navegador()

    try:

        # =================================
        # URL
        # =================================
        nome_carta_link = urllib.parse.quote(nome_carta)

        url = (
            "https://www.ligapokemon.com.br/"
            f"?view=cards/card"
            f"&card={nome_carta_link}"
            f"&ed={edicao}"
            f"&num={numero}"
        )

        print("URL:", url)

        # =================================
        # ABRE PÁGINA
        # =================================
        navegador.get(url)

        # espera carregar
        time.sleep(4)

        precos_finais = {}

        # =================================
        # PEGA TEXTO DA PÁGINA
        # =================================
        body = navegador.find_element(By.TAG_NAME, "body")

        texto_pagina = body.text

        # DEBUG
        print(texto_pagina[:3000])

        # =================================
        # NORMAL
        # =================================
        if "Normal" in texto_pagina:

            try:

                trecho = texto_pagina.split("Normal")[1][:1000]

                dados = extrair_precos(trecho)

                if dados:
                    precos_finais["normal"] = dados

            except:
                pass

        # =================================
        # FOIL
        # =================================
        if "Foil" in texto_pagina:

            try:

                trecho = texto_pagina.split("Foil")[1][:1000]

                dados = extrair_precos(trecho)

                if dados:
                    precos_finais["foil"] = dados

            except:
                pass

        # =================================
        # REVERSE FOIL
        # =================================
        if "Reverse Foil" in texto_pagina:

            try:

                trecho = texto_pagina.split("Reverse Foil")[1][:1000]

                dados = extrair_precos(trecho)

                if dados:
                    precos_finais["reverse_foil"] = dados

            except:
                pass

        # =================================
        # RESULTADO
        # =================================
        if len(precos_finais) > 0:
            print(f"ENCONTRADO: {nome_carta}")
        else:
            print("NENHUM PREÇO ENCONTRADO")

        # salva cache
        cache_precos[cache_key] = precos_finais

        return jsonify(precos_finais)

    except Exception as e:

        print("ERRO GERAL:", e)

        return jsonify({
            "erro": str(e)
        }), 500

    finally:

        try:
            navegador.quit()
        except:
            pass

# =========================================
# START
# =========================================
if __name__ == '__main__':

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
