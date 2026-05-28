import os
import time
import threading
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ── CREDENCIAIS ──────────────────────────────────────────────────────────────
ZAPI_SEND_URL = "https://api.z-api.io/instances/3F19CAAD49BB72F03C799E648AE68DF9/token/B77E6A0990899214EF21731D/send-text"
CLIENT_TOKEN  = "Ff0e29d550df049589cb4086ac3d8b843S"

# ── CONFIGURAÇÃO DA OFERTA ───────────────────────────────────────────────────
FRASE_GATILHO    = "fiquei interessada nas +300 dinâmicas de português"
DELAY_SEGUNDOS   = 90

MENSAGEM = """Oi! 👋 Que bom que você veio aqui, isso me diz que você é uma professora que leva o Português a sério, e eu quero te dar um presente por isso 🎁

Como você veio pelo WhatsApp, vou liberar pra você o Pacote Completo por apenas R$9,90, um desconto especial só pra quem chegou até mim pessoalmente.

No Pacote Completo você leva tudo: as +300 dinâmicas de Português prontas pra aplicar, organizadas por tema e faixa etária, mais todos os bônus exclusivos. Tudo pronto pra imprimir e usar amanhã na sua aula. 📚✨

Aqui está o link pra garantir agora: https://pay.wiapy.com/r2pvsFeMId

Qualquer dúvida é só falar aqui, tô aqui pra te ajudar! 🤗"""

PALAVRAS_BLOQUEIO = ["reembolso", "cancelar", "estorno", "devolver", "chargeback"]

# ── CONTROLE DE DUPLICATAS ───────────────────────────────────────────────────
respondidos = set()
lock = threading.Lock()

# ── FUNÇÕES ──────────────────────────────────────────────────────────────────
def pegar_texto(data):
    """Extrai o texto da mensagem independente do formato que a Z-API mandar."""
    # Percorre todos os valores do payload procurando uma string de texto
    for campo in ["text", "body", "caption"]:
        val = data.get(campo)
        if isinstance(val, str) and val.strip():
            return val.strip()

    # Campo message pode ser dict ou string
    msg = data.get("message")
    if isinstance(msg, str) and msg.strip():
        return msg.strip()
    if isinstance(msg, dict):
        for subcampo in ["conversation", "text", "caption"]:
            val = msg.get(subcampo)
            if isinstance(val, str) and val.strip():
                return val.strip()
        # extendedTextMessage
        ext = msg.get("extendedTextMessage")
        if isinstance(ext, dict):
            val = ext.get("text")
            if isinstance(val, str) and val.strip():
                return val.strip()

    return ""


def enviar(phone, mensagem):
    """Aguarda o delay e envia a mensagem via Z-API."""
    time.sleep(DELAY_SEGUNDOS)
    try:
        resp = requests.post(
            ZAPI_SEND_URL,
            json={"phone": phone, "message": mensagem},
            headers={"Content-Type": "application/json", "Client-Token": CLIENT_TOKEN},
            timeout=20
        )
        print(f"[ENVIADO] {phone} | status={resp.status_code} | {resp.text[:100]}")
    except Exception as e:
        print(f"[ERRO ENVIO] {phone} | {e}")


# ── WEBHOOK ──────────────────────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True, silent=True) or {}
    print(f"[PAYLOAD] {str(data)[:300]}")

    # Ignora mensagens próprias
    if data.get("fromMe") or data.get("isFromMe"):
        return jsonify(ok=True), 200

    # Pega o número
    phone = str(data.get("phone") or data.get("sender") or "").replace("@c.us", "").strip()
    if not phone:
        print("[IGNORADO] sem número")
        return jsonify(ok=True), 200

    # Pega o texto
    texto = pegar_texto(data)
    print(f"[TEXTO] '{texto[:120]}'")

    # Filtros
    if len(texto) < 15:
        print("[IGNORADO] texto curto")
        return jsonify(ok=True), 200

    lower = texto.lower()

    for p in PALAVRAS_BLOQUEIO:
        if p in lower:
            print(f"[IGNORADO] bloqueio: {p}")
            return jsonify(ok=True), 200

    if FRASE_GATILHO not in lower:
        print("[IGNORADO] sem gatilho")
        return jsonify(ok=True), 200

    # Duplicata
    with lock:
        if phone in respondidos:
            print(f"[IGNORADO] duplicata: {phone}")
            return jsonify(ok=True), 200
        respondidos.add(phone)

    # Agenda resposta em thread separada
    threading.Thread(target=enviar, args=(phone, MENSAGEM), daemon=True).start()
    print(f"[AGENDADO] {phone} em {DELAY_SEGUNDOS}s")
    return jsonify(ok=True), 200


@app.route("/", methods=["GET"])
def health():
    return jsonify(status="ativo", bot="+300 Dinamicas de Portugues"), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
