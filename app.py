"""Web interface for the campus regulations agent.

    streamlit run app.py
"""
import json
from pathlib import Path

import streamlit as st
from openai import APIError

import agent
from retrieval import EMBED_MODEL, article_text, article_title

SOURCES = json.loads((Path(__file__).parent / "data" / "regulations" / "sources.json").read_text(encoding="utf-8"))

st.set_page_config(page_title="ODTÜ KKK Yönetmelik Asistanı", page_icon="📚")
st.title("📚 ODTÜ KKK Yönetmelik Asistanı")
st.caption(
    "Lisans Eğitim Öğretim Yönetmeliği (2026) hakkındaki sorularınızı yanıtlar ve dayandığı maddeyi gösterir. "
    "Resmî bir hizmet değildir; bağlayıcı metin yönetmeliğin kendisidir."
)

with st.sidebar:
    st.subheader("Sistem")
    st.markdown(
        f"**Sohbet modeli**\n`{agent.MODEL}`\n\n"
        f"**Arama modeli**\n`{EMBED_MODEL}`\n\n"
        "**Kaynak belgeler**"
    )
    for source in SOURCES:
        st.markdown(f"- [{source['title']}]({source['url']})  \n  _indirildi: {source['retrieved_at']}_")
    st.divider()
    st.markdown(
        "Asistan yalnızca yönetmelikte bulduğu maddelere dayanarak cevap verir. "
        "Gösterdiği her madde, o konuşmada gerçekten aramadan dönmüş olmak zorundadır; "
        "aksi halde cevap reddedilir ve yeniden yazdırılır."
    )
    if st.button("Sohbeti temizle"):
        st.session_state.clear()
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": agent.SYSTEM_PROMPT}]
    st.session_state.retrieved = set()
    st.session_state.history = []  # what we show on screen: (question, answer, sources)

for question, answer, sources in st.session_state.history:
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        st.write(answer)
        for source in sources:
            number = int(source.split()[1])
            with st.expander(f"📄 {source} – {article_title(number)}"):
                st.write(article_text(number))

question = st.chat_input("Örneğin: Bir dönemde en fazla kaç ders alabilirim?")
if question:
    with st.chat_message("user"):
        st.write(question)

    st.session_state.messages.append({"role": "user", "content": question})
    turn_start = len(st.session_state.messages) - 1

    with st.chat_message("assistant"):
        with st.status("💭 Düşünüyor...", expanded=True) as status:
            try:
                result = agent.run_agent(
                    st.session_state.messages,
                    st.session_state.retrieved,
                    on_status=lambda text: status.update(label=text),
                )
                status.update(label="Cevap doğrulandı", state="complete", expanded=False)
            except APIError as error:
                status.update(label="⚠️ API hatası", state="error")
                del st.session_state.messages[turn_start:]  # drop the unfinished turn
                st.error(f"Model şu anda cevap veremedi: {error}. Lütfen tekrar deneyin.")
                st.stop()

        st.write(result.answer)
        for source in result.sources:
            number = int(source.split()[1])
            with st.expander(f"📄 {source} – {article_title(number)}"):
                st.write(article_text(number))

    st.session_state.history.append((question, result.answer, result.sources))
