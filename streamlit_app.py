from openai import OpenAI
import streamlit as st

from PubmedSearcher import PubmedSearcher

st.sidebar.title("Pubmed Assistant")
st.sidebar.image("./pubmed_assistant.png")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo-1106"

if "messages" not in st.session_state:
    st.session_state.messages = []

if st.sidebar.button("Clear Chat"):
    st.session_state.messages = []

@st.cache_resource
def pubmed_searcher():
    return PubmedSearcher()
searcher = pubmed_searcher()

def user_prompt(query, articles):
    abstracts = "\n\n".join([article.abstract for article in articles])
    return f"According to query: {query}, the relevant research articles are as follows:\n\n{abstracts}.\n\nSummarize all research articles into one paragraph."

def reference(articles):
    return "**Reference**:\n" + "\n\n".join([f"- [{article.title}]({article.url})" for article in articles])

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Message Pubmed Assistant"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    articles = searcher.search(prompt, 5)
    articles = [article for article in articles if article.abstract is not None]

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        for response in client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ] + [{"role": "user", "content": user_prompt(prompt, articles)}],
            stream=True,
        ):
            full_response += (response.choices[0].delta.content or "")
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)
        st.markdown(reference(articles))
    st.session_state.messages.append({"role": "assistant", "content": f"{full_response}\n{reference(articles)})"})