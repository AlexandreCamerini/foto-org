"""Interface Streamlit — fala com o backend FastAPI via HTTP (porta 8000)."""

from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

API_BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="Organizador de Fotos", page_icon="🖼️", layout="wide")
st.title("🖼️ Organizador de Fotos")
st.caption("Varre pastas do seu Mac, cataloga, acha duplicatas e sugere agrupamento por viagem/local.")


def _api_get(path: str, **kwargs):
    try:
        resposta = requests.get(f"{API_BASE_URL}{path}", timeout=30, **kwargs)
        resposta.raise_for_status()
        return resposta.json(), None
    except requests.exceptions.ConnectionError:
        return None, f"Não consegui falar com o backend em {API_BASE_URL}. Ele está rodando (uvicorn app.main:app)?"
    except requests.exceptions.RequestException as erro:
        return None, str(erro)


def _api_post(path: str, json: dict):
    try:
        resposta = requests.post(f"{API_BASE_URL}{path}", json=json, timeout=600)
        resposta.raise_for_status()
        return resposta.json(), None
    except requests.exceptions.ConnectionError:
        return None, f"Não consegui falar com o backend em {API_BASE_URL}. Ele está rodando (uvicorn app.main:app)?"
    except requests.exceptions.RequestException as erro:
        return None, str(erro)


aba_scan, aba_fotos, aba_duplicatas, aba_sugestoes = st.tabs(
    ["📂 Varrer pastas", "🗂️ Todas as fotos", "🪞 Duplicatas", "🧭 Sugestões de agrupamento"]
)

with aba_scan:
    st.subheader("Varrer diretórios")
    diretorios_texto = st.text_area(
        "Um caminho de pasta por linha (ex.: /Users/voce/Pictures/Viagens)",
        height=120,
        placeholder="/Users/voce/Pictures/Viagens\n/Users/voce/Desktop/Fotos soltas",
    )
    if st.button("Varrer agora", type="primary"):
        diretorios = [linha.strip() for linha in diretorios_texto.splitlines() if linha.strip()]
        if not diretorios:
            st.warning("Cola pelo menos um caminho de pasta.")
        else:
            with st.spinner("Varrendo — pode demorar em coleções grandes (calcula hash de cada foto)..."):
                resultado, erro = _api_post("/scan", {"diretorios": diretorios})
            if erro:
                st.error(erro)
            else:
                st.success(
                    f"Encontradas {resultado['fotos_encontradas']} fotos — "
                    f"{resultado['fotos_novas']} novas, "
                    f"{resultado['fotos_ja_catalogadas']} já catalogadas"
                    + (f", {resultado['fotos_com_erro']} com erro" if resultado["fotos_com_erro"] else "")
                    + "."
                )

with aba_fotos:
    st.subheader("Catálogo")
    if st.button("Recarregar", key="reload_fotos"):
        st.rerun()
    fotos, erro = _api_get("/photos")
    if erro:
        st.error(erro)
    elif not fotos:
        st.info("Nenhuma foto catalogada ainda — vai na aba 'Varrer pastas'.")
    else:
        df = pd.DataFrame(fotos)
        st.metric("Total de fotos", len(df))
        st.dataframe(
            df[
                [
                    "nome_arquivo",
                    "pasta_fonte",
                    "tamanho_bytes",
                    "data_exif",
                    "sugestao_agrupamento",
                    "score_confianca",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

with aba_duplicatas:
    st.subheader("Duplicatas encontradas")
    if st.button("Recarregar", key="reload_dup"):
        st.rerun()
    dados, erro = _api_get("/duplicates")
    if erro:
        st.error(erro)
    elif not dados or dados["total_grupos"] == 0:
        st.info("Nenhuma duplicata encontrada (ou nenhuma foto catalogada ainda).")
    else:
        st.metric("Espaço que dá pra economizar", f"{dados['espaco_total_economizavel_mb']} MB")
        for i, grupo in enumerate(dados["grupos"], start=1):
            tipo_label = "Idênticas (mesmo arquivo)" if grupo["tipo"] == "exata" else "Parecidas (similaridade visual)"
            with st.expander(f"Grupo {i} — {tipo_label} ({len(grupo['fotos'])} fotos)"):
                st.dataframe(pd.DataFrame(grupo["fotos"]), use_container_width=True, hide_index=True)
                st.caption(f"Economiza {round(grupo['espaco_desperdicado_bytes'] / (1024 * 1024), 2)} MB mantendo só uma.")

with aba_sugestoes:
    st.subheader("Sugestões de agrupamento")
    if st.button("Recarregar", key="reload_sug"):
        st.rerun()
    sugestoes, erro = _api_get("/suggestions")
    if erro:
        st.error(erro)
    elif not sugestoes:
        st.info("Nenhuma sugestão ainda — cadastre fotos primeiro.")
    else:
        df = pd.DataFrame(sugestoes)
        agrupado = (
            df.groupby("sugestao_agrupamento")
            .agg(fotos=("photo_id", "count"), confianca_media=("score_confianca", "mean"))
            .reset_index()
            .sort_values("fotos", ascending=False)
        )
        agrupado["confianca_media"] = agrupado["confianca_media"].round(2)
        st.dataframe(agrupado, use_container_width=True, hide_index=True)
