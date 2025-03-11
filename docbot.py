import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
import google.generativeai as genai
import openai
import os
import tempfile
import pdfplumber
import pypandoc
from docx import Document as DocxDocument
import sqlite3
import hashlib
import time


genai.configure(api_key=st.secrets["gemini"]["api_key"])
model = genai.GenerativeModel("gemini-1.5-flash-8b")

if "username" not in st.session_state:
    st.session_state.username = "Default User"
if "autheticated" not in st.session_state:
    st.session_state.autheticated = False
conn = sqlite3.connect('user_data.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT)''')
conn.commit()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def add_user_to_db(username, hashed_password):
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
    conn.commit()

def check_user_in_db(username):
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    return c.fetchone()

def create_chat_history_table():
    try:
        conn = sqlite3.connect("chat_history.db")
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS chat_history (username TEXT, question TEXT, answer TEXT)''')
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Error creating table: {e}")
        print(f"Error creating table: {e}")

def save_chat_history(username, question, answer):
    try:
        create_chat_history_table()
        conn = sqlite3.connect("chat_history.db")
        c = conn.cursor()
        c.execute("INSERT INTO chat_history (username, question, answer) VALUES (?, ?, ?)", (username, question, answer))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Error saving chat history: {e}")
        print(f"Error saving chat history: {e}")

def get_chat_history(username):
    try:
        conn = sqlite3.connect("chat_history.db")
        c = conn.cursor()
        c.execute("SELECT question, answer FROM chat_history WHERE username=?", (username,))
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception as e:
        st.error(f"Error fetching chat history: {e}")
        return []

def authenticate_user(username, password):
    user = check_user_in_db(username)
    if user and hash_password(password) == user[0]:
        st.session_state.authenticated = True
        st.session_state.username = username
        st.rerun()
        return True
    return False

def register_user(username, password):
    conn = sqlite3.connect("user_data.db")
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE username=?", (username,))
    if c.fetchone():
        return False, "Username already exists"
    else: 
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        conn.close()
        return True, "User registered successfully"

if "registered" not in st.session_state:
    st.session_state.registered = False
if st.session_state.registered:
    st.session_state.registered = False

def delete_user(username):
    try:
        conn = sqlite3.connect("chat_history.db")
        c = conn.cursor()
        c.execute("DELETE FROM chat_history WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        st.session_state.chat_history = []

        conn = sqlite3.connect("user_data.db")
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        st.session_state.chat_history = []
        st.success("")
    except Exception as e:
        st.error(f"Error deleting user data : {str(e)}")

def logout():
    if "username" in st.session_state:
        # delete_user(st.session_state.username)
        st.session_state.username = "Default User"
        st.session_state.authenticated = False
        st.success("Logged out successfully")
    else:
        st.write("You are not logged in.")
# def logout():
#     if "username" in st.session_state:
#         delete_user(st.session_state.username)  # Delete the logged-in user's data
#         st.session_state.username = "Default User"
#         st.session_state.authenticated = False
#         st.success("Logged out successfully.")
#     else:
#         st.write("You are not logged in.")

def about_page():
    st.title("About This App")
    st.markdown("""
    ## Welcome to DocBot! 
    Docbot is your intelligent assistant for efficient document navigation. It supports:
    
    - Text Extraction from PDFs.
    - Document summarization and key points to help you quickly understand long documnets.
    - Translation capabilities to convert documents to different languages.
    - File Format Conversion between PDF, DOCS and TXT.
    
    ### Key Features:
    - User Authentication: Sign in to personalize your experience and save your documents & preferences.
    - Multi-language support: Translates documents to different languages with ease.
    - Chat Interface: Ask questions and get answers based on your documents.
    - Users can view their past history by navigating through Chat history button on the header.

    ### Why DocBot?
    Navigating large documents can be tedious and time consuming.Docbot simd to dtresmline this process and save you time by providing intelligent text extraction, summarization, and easy navigation features. 
    It is designed for professionals, students and anyone who is dealing with large documents.

    ### How to use?
    1. Upload a PDF
    2. Ask question related to document, and get instant answers.
    3. Use tranlation or conversion features for better accessibility.            
                
        """)

if "show_about" not in st.session_state:
    st.session_state.show_about = False

def show_authentication_page():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'show_about' not in st.session_state:
        st.session_state.show_about = False
    if not st.session_state.authenticated:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("Know the App Better"):
            st.session_state.show_about = not  st.session_state.show_about
        if st.session_state.show_about:
            about_page()
        st.title("OR")
        tab1, tab2 = st.tabs(["Sign In", "Register"])
        with tab1: 
            with st.form("Sign In Form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                sign_in_button = st.form_submit_button("Sign In")
                if sign_in_button:
                    if authenticate_user(username, password):
                        st.session_state.authenticated = True
                        st.success(f"Welcome back,{username}!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
        with tab2:
            with st.form("Registration Form"):
                new_username = st.text_input("New Username")
                new_password = st.text_input("New Password", type="password")
                register_button = st.form_submit_button("Register")
                if register_button:
                    success, message =  register_user(new_username, new_password)
                    if success:
                        st.session_state.show_about = False
                        st.success(message)
                    else:
                        st.error(message)
   
def loads_css(css_file):
    with open(css_file, "r") as f:
        css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

def navigate(new_page):
    st.query_params["page"] = new_page
    
def navigation():
    if 'authenticated' in st.session_state and st.session_state.authenticated:
        col1, col2, col3, col4 = st.columns([1,1,1,1])
        with col1:
            if st.button("Home"):
                navigate("home")
                st.rerun()
        with col2:
            if st.button("About"):
                navigate("about")
                st.rerun()
        with col3:
            if st.button("Chat History"):
                navigate("chat-history")
                st.rerun()
        with col4:
            if st.button("Logout"):
                logout()
                st.session_state.username = "Default User"
                st.session_state.authenticated = False
                #st.success("Logged out succesfully")
                time.sleep(1)  # 1-second delay
                st.rerun()
                
    else:
        st.write("")

def file_upload():
    if 'authenticated' in st.session_state and st.session_state.authenticated:
        st.markdown('<div class="file-uploader">', unsafe_allow_html= True)
        uploaded_file = st.file_uploader("Choose a file", type= ["pdf"], label_visibility="collapsed")
        if uploaded_file:
            st.session_state.uploaded_file = uploaded_file
            st.markdown(f"Uploaded file:{uploaded_file.name}")
            if st.button("Remove File"):
                st.session_state.uploaded_file = None
                st.warning("File has been removed")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.write("")

def pdf_processor():
    if "uploaded_file" in st.session_state and st.session_state.uploaded_file:
        uploaded_file = st.session_state.uploaded_file
        if "pdf_text" not in st.session_state:
            with st.spinner("Processing document..."):
                pdf_reader = PdfReader(uploaded_file)
                st.session_state.pdf_text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
            st.success("Extracted Text", st.session_state.pdf_text, height=300)

def extract_txt_from_pdf(uploaded_file):
    pdf_reader = PdfReader(uploaded_file)
    full_text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
    return full_text

def generate_doc_metadata(pdf_text):
    prompt = f"""
    You are an AI assistant that processes documents and extracts key details.

    Based on the following document text, strictly provide ONLY the following sections:
    1. **Title** (if mentioned, otherwise generate a relevant one).
    
    2. **Number of pages** (count the number of pages).

    3. **Summary** (3-5 sentences).

    4. **Key Points** (bullet format).

    Format your response as follows:
    **Title:** [Extracted Title]
    <br>

    **Number of pages** [Extracted Count]

    **Summary**
    - [Sentence 1]
    - [Sentence 2]
    - [Sentence 3]

    **Key Points**
    - [Point 1]
    - [Point 2]
    - [Point 3]

    Here is the document text:
    {pdf_text}

    """
    try:
        response = model.generate_content(prompt)
        text = response.text
        if "Key Points:" in text:
            text = text.split("Key Points:")[0] + "Key Points:\n" + text.split("Key Points:")[1].split("\n\n")[0]
        formatted_text = text.replace("**", "<b>").replace("[", "").replace("]", "</b>")
        return formatted_text
    except openai.OpenAIError as e:
        return f"Error: {str(e)}"

def translation_with_openai(full_text, target_language):
    prompt = f"""
    You are a translation assistant. Translate the user's text into {target_language}.
    Provide ONLY the translated text without any additional comments, explanations, or prefixes.

    Here is the text to translate:
    {full_text}
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except openai.OpenAIError as e:
        return f"Translation failed: {str(e)}"

def convert_file_format(uploaded_file, target_format):
    input_format = uploaded_file.name.split('.')[-1].lower()
    temp_file_path = tempfile.NamedTemporaryFile(delete=False).name
    uploaded_file_path = f"{temp_file_path}.{input_format}"
    with open(uploaded_file_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    output_file_path = f"{temp_file_path}.{target_format}"
    try:
        if input_format == "pdf" and target_format == "txt":
            with pdfplumber.open(uploaded_file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
        elif input_format == "pdf" and target_format == "docx":
            with pdfplumber.open(uploaded_file_path) as pdf:
                doc = DocxDocument()
                for page in pdf.pages:
                    text = page.extract_text()
                    doc.add_paragraph(text)
                doc.save(output_file_path)
        elif input_format == "pdf" and target_format == "pdf":
            with open(uploaded_file_path, 'rb') as f:
                reader = PdfReader(f)
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)
                with open(output_file_path, 'wb') as output_pdf:
                    writer.write(output_pdf)
        else:
            pypandoc.convert_file(uploaded_file_path,target_format, outputfile=output_file_path)
        with open(output_file_path, 'rb') as f:
            converted_data = f.read()

        return converted_data
    except Exception as e:
        return f"Conversion failed :{e}"
    finally:
        if os.path.exists(uploaded_file_path):
            os.remove(uploaded_file_path)
        if os.path.exists(output_file_path):
            os.remove(output_file_path)

def translate_doc(uploaded_file):
    if "translated_text" not in st.session_state:
        st.session_state.translated_text = ""
    if "target_language" not in st.session_state:
        st.session_state.target_language = "en"
    if "last_file.name" not in st.session_state:
        st.session_state.last_file_name = None
    if uploaded_file:
        with st.expander("Translate Document", expanded=True):
            language_options = {
                "en": "English",
                "es": "Spanish",
                "fr": "French",
                "de": "German",
                "zh": "Chinese (Simplified)",
                "ja": "Japanese",
                "ko": "Korean",
                "it": "Italian",
                "nl": "Dutch",
                "pl": "Polish",
                "hi": "Hindi",
                "pt": "Portuguese",
                "ru": "Russian",
                "sv": "Swedish",
                "da": "Danish",
                "fi": "Finnish",
                "tr": "Turkish",
                "ar": "Arabic",
                "cs": "Czech",
                "el": "Greek",
                "id": "Indonesian",
                "ro": "Romanian",
                "uk": "Ukrainian",
            }
            selectbox_key =f"language_selector_{uploaded_file.name}"
        
            new_language = st.selectbox(
                "Select the target language for translation",
                options=list(language_options.keys()),
                format_func=lambda x: f"{x.upper()} - {language_options[x]}",
                key=selectbox_key
            )
            if new_language !=st.session_state.target_language or st.session_state.last_file_name != uploaded_file.name:
                st.session_state.target_language = new_language
                st.session_state.last_file_name = uploaded_file.name

                with st.spinner(f"Translating to {language_options[new_language]}...."):
                    full_text = extract_txt_from_pdf(uploaded_file)
                    st.session_state.translated_text = translation_with_openai(full_text, new_language)

            if st.session_state.translated_text:
                st.write("### Translated Document")
                st.text_area("Preview", st.session_state.translated_text, height=300)
                txt_file = st.session_state.translated_text.encode('utf-8')
                st.download_button(
                    label = "Download Translated Document",
                    data = txt_file,
                    file_name = "translated_document.txt",
                    mime = "text/plain",
                    key= "download_translated_document"
                )

def ask_chatgpt(pdf_text, user_question):
    try:
        prompt = f"Document text:\n{pdf_text}\n\nQuestion: {user_question}\nAnswer:"
        response = model.generate_content(prompt)
        answer = response.text
        return answer
    except Exception as e:
        return f"Error: {str(e)}"
    
def process_input():
    user_question = st.session_state.user_input
    if user_question:
        with st.spinner("Fetching answer..."):
            response = ask_chatgpt(st.session_state.pdf_text, user_question)
        st.session_state.chat_history.append({"question": user_question, "answer": response})
        save_chat_history(st.session_state.username, user_question, response)
        st.session_state.user_input = ''

def display_chat_history():
    if 'username' in st.session_state:
        chat_history = get_chat_history(st.session_state.username)
        if chat_history:
            st.markdown("<h1 style='text-align:center;'>Chat History</h1>", unsafe_allow_html=True)
            for chat in chat_history:
                user_message = f"""
                    <div class="chat-box" <strong>You:</strong> {chat[0]}
                    </div>
                """
                assistant_message = f"""
                    <div class="chat-box" <strong>Assistant:</strong> {chat[1]}
                    </div>
                """
                st.markdown(user_message, unsafe_allow_html=True)
                st.markdown(assistant_message, unsafe_allow_html=True)
                chat_content = generate_downloadable_chat(st.session_state.chat_history)
            st.download_button(
                label="Download Chat History",
                data=chat_content,
                file_name="chat_history.txt",
                mime="text/plain",
                key="download_chat_history_main_1"
            )
        else:
            st.write("No chat history found")
    else:
        st.write("Please login to view chat history")

if 'chat-history' in st.session_state:
    display_chat_history()
else:
    show_authentication_page()
def load_chat_history(username):
    try:
        conn = sqlite3.connect("chat_history.db")
        c = conn.cursor()
        c.execute("SELECT question, answer FROM chat_history WHERE username=?", (username,))
        rows = c.fetchall()
        conn.close()
        if rows:
            st.session_state.chat_history = [{"question": row[0], "answer": row[1]} for row in rows]
        else:
            st.session_state.chat_history = []
    except Exception as e:
        st.error(f"Error loading chat history: {e}")

if "username" in st.session_state:
    load_chat_history(st.session_state.username)
else:
    st.write("Please log in to view chat history.") 


def generate_downloadable_chat(chat_history):
    chat_content = ""
    for chat in chat_history:
        chat_content += f"You: {chat['question']}\nAssistant: {chat['answer']}\n\n"
    return chat_content
if not os.path.exists('chat_history.db'):
    st.error("Database file  not found.")

def get_file_hash(uploaded_file):
    if uploaded_file is None:
        return None
    file_bytes = uploaded_file.getvalue()
    return hashlib.md5(file_bytes).hexdigest()

def convert_document_format(uploaded_file):
    if uploaded_file:
        with st.expander("Convert Document Format", expanded=True):
            convert_format = st.selectbox("Select file format to",["txt", "pdf", "docx"])
            if st.button("Convert"):
                converted_file = convert_file_format(uploaded_file, convert_format)
                if isinstance(converted_file, str) and converted_file.startswith("Error"):
                    st.error(converted_file)
                else:
                    st.download_button(
                        label=f"Download {convert_format} file",
                        data=converted_file,
                        file_name=f"converted_document.{convert_format}",
                        mime="application/octed-stream",
                        key=f"download_converted_{convert_format}"
                    )
            else:
                st.write()

def question_answer(uploaded_file, extract_txt_from_pdf, process_input):
    if uploaded_file:
        if "pdf_text" not in st.session_state:
            with st.spinner("Processing doocument..."):
                st.session_state.pdf_text = extract_txt_from_pdf(uploaded_file)
        if 'chat_history' in st.session_state and st.session_state.chat_history:
            last_chat = st.session_state.chat_history[-1]
            user_message = f"""
                <div class="chat-box" <strong>You:</strong> {last_chat['question']}
            """
            assistant_message = f"""
                <div class="chat-box" <strong>Assistant:</strong> {last_chat['answer']}
            """
            st.markdown(user_message, unsafe_allow_html=True)
            st.markdown(assistant_message, unsafe_allow_html=True)
        st.text_input("Ask a question about the document:", key="user_input", on_change=process_input)
    else:
        st.write()

def display_home():
    if 'authenticated' in st.session_state and st.session_state.authenticated:
        st.markdown('<h1 style="text-align: center;">DocBot 🤖 </h1>', unsafe_allow_html=True)
        file_upload()
        uploaded_file = st.session_state.get('uploaded_file')
        col1, col2 = st.columns([23, 27])
        with col2:
            if uploaded_file:
                if 'previous_uploaded_file' not in st.session_state or uploaded_file.name != st.session_state['previous_uploaded_file']:
                    st.session_state['chat_history'] = []
                    st.session_state['previous_uploaded_file'] = uploaded_file.name
                pdf_text = extract_txt_from_pdf(uploaded_file)
                if "metadata" not in st.session_state:
                    st.session_state.metadata = generate_doc_metadata(pdf_text)
                metadata = st.session_state.metadata
                st.write("### Document Metadata")
                st.markdown(f"<div class='white-background'>{metadata}</div>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                st.download_button(
                    label="Download Document overview",
                    data=str(metadata),
                    file_name="document_overview.txt",
                    mime="text/plain",
                )
            else:
                st.write()
        with col1:
            if uploaded_file:
                translate_doc(uploaded_file)
            else:
                st.write()
        with col1:
            if uploaded_file:
                convert_document_format(uploaded_file)
            else:
                st.write()
        st.markdown("<br>", unsafe_allow_html=True)
        if uploaded_file:
            question_answer(uploaded_file, extract_txt_from_pdf, process_input)
        else:
            st.write()

def display_about():
    about_page()

loads_css("docbot.css")
query_params = st.query_params
page = query_params.get("page", "home")

navigation()

if page == "home":
    display_home()
if page == "about":
    display_about()
if page == "chat-history":
    display_chat_history()

