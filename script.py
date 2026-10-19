
from pathlib import Path
from email import policy
from email.parser import BytesParser
from email.header import decode_header, make_header
import csv
import re

PALAVRAS = {
    "encomenda": [
        "correios", "encomenda", "parcel", "package",
        "delivery", "shipping", "tracking"
    ],
    "cobranca": [
        "taxa", "fee", "customs", "payment",
        "pagamento", "reembolso", "refund"
    ],
    "urgencia": [
        "retido", "held", "urgent", "urgente",
        "suspended", "suspenso", "action required"
    ],
}

def decodificar(valor):
    if not valor:
        return ""
    try:
        return str(make_header(decode_header(str(valor))))
    except (ValueError, TypeError):
        return str(valor)

def obter_texto(msg):
    partes = []
    for parte in msg.walk():
        if parte.get_content_maintype() == "multipart":
            continue
        if parte.get_content_disposition() == "attachment":
            continue
        if parte.get_content_type() not in ("text/plain", "text/html"):
            continue
        try:
            conteudo = parte.get_content()
            if isinstance(conteudo, str):
                partes.append(conteudo)
        except (LookupError, UnicodeError, ValueError):
            continue
    return "\n".join(partes)

def encontrar_termos(texto):
    texto = texto.casefold()
    encontrados = {}
    for categoria, termos in PALAVRAS.items():
        encontrados[categoria] = [
            termo for termo in termos
            if re.search(
                r"(?<!\w)" + re.escape(termo) + r"(?!\w)",
                texto
            )
        ]
    return encontrados

def main():
    pasta = Path(input("Caminho da pasta do corpus: ").strip().strip('"'))

    if not pasta.is_dir():
        print("Pasta não encontrada. Confira o caminho.")
        return

    arquivos = [
        arquivo for arquivo in pasta.rglob("*")
        if arquivo.is_file() and arquivo.suffix.lower() == ".eml"
    ]

    print(f"Arquivos EML encontrados: {len(arquivos)}")
    resultados = []

    for indice, arquivo in enumerate(arquivos, start=1):
        try:
            with arquivo.open("rb") as f:
                msg = BytesParser(policy=policy.default).parse(f)

            assunto = decodificar(msg.get("Subject", ""))
            remetente = decodificar(msg.get("From", ""))
            data = decodificar(msg.get("Date", ""))
            texto = obter_texto(msg)

            categorias = encontrar_termos(assunto + "\n" + texto)
            pontuacao = sum(len(termos) for termos in categorias.values())

            if pontuacao > 0:
                resultados.append({
                    "arquivo": str(arquivo.relative_to(pasta)),
                    "pontuacao": pontuacao,
                    "assunto": assunto,
                    "remetente": remetente,
                    "data_declarada": data,
                    "encomenda": ", ".join(categorias["encomenda"]),
                    "cobranca": ", ".join(categorias["cobranca"]),
                    "urgencia": ", ".join(categorias["urgencia"]),
                })

            if indice % 100 == 0:
                print(f"Processados: {indice}/{len(arquivos)}")

        except Exception as erro:
            print(f"Falha ao ler {arquivo.name}: {erro}")

    resultados.sort(key=lambda item: item["pontuacao"], reverse=True)

    saida = Path.home() / "Documents" / "resultado_triagem.csv"
    campos = [
        "arquivo", "pontuacao", "assunto", "remetente",
        "data_declarada", "encomenda", "cobranca", "urgencia"
    ]

    with saida.open("w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(resultados)

    print(f"\nCandidatos encontrados: {len(resultados)}")
    print(f"Relatório salvo em: {saida}")
    print("\n10 primeiros candidatos:")

    for item in resultados[:10]:
        print(
            f'{item["pontuacao"]:>2} | '
            f'{item["assunto"][:80]} | {item["arquivo"]}'
        )

if __name__ == "__main__":
    main()
