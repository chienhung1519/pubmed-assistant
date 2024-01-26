from openai import OpenAI
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import datetime
import pandas as pd

from PubmedSearcher import PubmedSearcher

# Setup session states
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo-1106"

if "messages" not in st.session_state:
    st.session_state.messages = []

# Setup resources
@st.cache_resource
def pubmed_searcher():
    return PubmedSearcher()
searcher = pubmed_searcher()

@st.cache_resource
def openai_client():
    return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
client = openai_client()

@st.cache_resource
def gsheet_connection():
    return st.connection("gsheets", type=GSheetsConnection)
conn = gsheet_connection()

# Prompt functions
def user_prompt(query, articles):
    abstracts = "\n\n".join([article.abstract for article in articles])
    return f"According to query: {query}, the relevant research articles are as follows:\n\n{abstracts}.\n\nSummarize all research articles into one paragraph."

def reference(articles):
    return "\n**Reference**:\n" + "\n\n".join([f"- [{article.title}]({article.url})" for article in articles])

# Setup sidebar
st.sidebar.title("Pubmed Assistant")
st.sidebar.image("./images/pubmed_assistant.png")

if st.sidebar.button("Clear Chat"):
    st.session_state.messages = []

# Greeter
if st.session_state.messages == []:
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": "Hi, I'm your Pubmed Assistant. I can help you find relevant research articles and summarize them for you. Type your query below.",
        }
    )

# Chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Message Pubmed Assistant"):
    # User prompt
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Retrieve articles and filter out those without abstracts
    articles = searcher.search(prompt, 5)
    articles = [article for article in articles if article.abstract is not None]

    # OpenAI chat
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        # Add articles to prompt and stream response
        for response in client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages[:-1] # Exclude last message
            ] + [{"role": "user", "content": user_prompt(prompt, articles)}], # Include articles
            stream=True,
        ):
            full_response += (response.choices[0].delta.content or "")
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(f"{full_response}\n{reference(articles)}")
    st.session_state.messages.append({"role": "assistant", "content": f"{full_response}\n{reference(articles)}"})

    # Update Google Sheets
    data = conn.read(usecols=[0, 1, 2, 3], ttl=0) # ttl=0 to avoid caching
    new_data = pd.DataFrame({
        "time": [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")], 
        "user": [prompt], 
        "response": [full_response], 
        "reference": [reference(articles)]
    })
    data.dropna(inplace=True)
    data = pd.concat([data, new_data], axis=0)
    conn.update(data=data)