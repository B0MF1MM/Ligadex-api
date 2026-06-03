import urllib.parse
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
import requests

app = Flask(__name__)
CORS(app)

cache_precos = {}


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
    try:
        print(f"URL ALVO: {url}", flush=True)
        
        # Coloque a sua chave do ScraperAPI aqui
        SCRAPER_API_KEY = "72a4e794eb83856fcfbfd305bc33c250" 
        
        # Monta a URL do proxy passando o site da liga como parâmetro
        proxy_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={url}"
        
        # Faz a requisição padrão (o Proxy lida com a Cloudflare)
        response = requests.get(proxy_url)
        
        if response.status_code != 200:
            print(f"ERRO HTTP: {response.status_code}", flush=True)
            return {}

        html = response.text
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

        print(f"RESULTADO: {resultados}", flush=True)
        return resultados

    except Exception as e:
        print(f"ERRO: {e}", flush=True)
        return {}


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
    try:
        url = request.args.get(
            "url",
            "https://www.ligapokemon.com.br/?view=cards/card&card=Kakuna%20%28002%2F086%29&ed=CRI&num=002"
        )
        
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url)
        
        texto = BeautifulSoup(response.text, "html.parser").get_text(" ")
        return jsonify({
            "url": url,
            "status_code": response.status_code,
            "tamanho": len(texto),
            "trecho": texto[:3000],
        })
    except Exception as e:
        return jsonify({"erro": str(e)})


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "cache": len(cache_precos)}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)