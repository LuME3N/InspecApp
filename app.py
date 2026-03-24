import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. Veilig de API Key ophalen
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"⚠️ API Key probleem: {e}")
    st.stop()

# 2. App instellingen
st.set_page_config(page_title="ElektraVision AI", layout="wide")
st.title("⚡ Elektra-Assistent AI")

# 3. Model selectie - Gebruik de meest stabiele naam
# We laten 'latest' en 'v1beta' weg om conflicten te voorkomen
model = genai.GenerativeModel('gemini-1.5-flash')

# 4. Interface
bron = st.radio("Foto toevoegen via:", ["Camera", "Bladeren (Galerij)"])

if bron == "Camera":
    img_file = st.camera_input("Maak een foto van de verdeelkast")
else:
    img_file = st.file_uploader("Kies een afbeelding", type=['png', 'jpg', 'jpeg'])

if img_file is not None:
    img = Image.open(img_file)
    st.image(img, caption="Geselecteerde afbeelding", width=300)
    
    if st.button("Analyseer Groepen"):
        with st.spinner("AI analyseert de componenten..."):
            try:
                # Instructie voor de AI
                prompt = """
                Kijk naar deze foto van een elektra verdeelkast.
                Maak een lijst van alle groepen in een tabel:
                - Nummer
                - Type (bijv. B16)
                - Functie
                """
                
                # De aanroep
                response = model.generate_content([prompt, img])
                
                if response.text:
                    st.success("Analyse voltooid!")
                    st.markdown(response.text)
                else:
                    st.warning("De AI kon geen tekst genereren uit deze foto.")
            
            except Exception as e:
                # Als het nog steeds misgaat, tonen we de exacte fout
                st.error(f"Er ging iets mis: {e}")
                st.info("Check of je API-key wel actief is in Google AI Studio.")
