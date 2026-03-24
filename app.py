import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. Veilig de API Key ophalen
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ API Key niet gevonden in Secrets! Voeg GEMINI_API_KEY toe.")
    st.stop()

# 2. App instellingen
st.set_page_config(page_title="ElektraVision AI", layout="wide")
st.title("⚡ Elektra-Assistent AI")

# 3. Model selectie - Aangepast naar de nieuwste stabiele versie
# We gebruiken 'gemini-1.5-flash-latest' voor de beste ondersteuning
try:
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except:
    # Backup als de naam in de toekomst verandert
    model = genai.GenerativeModel('gemini-1.5-flash')

# 4. De Keuzeknop voor Foto-bron
bron = st.radio("Kies hoe je de foto wilt toevoegen:", ["Camera", "Bladeren (Galerij/Upload)"])

# 5. Het input veld
img_file = None
if bron == "Camera":
    img_file = st.camera_input("Maak een foto van de verdeelkast")
else:
    img_file = st.file_uploader("Kies een afbeelding", type=['png', 'jpg', 'jpeg'])

if img_file is not None:
    img = Image.open(img_file)
    st.image(img, caption="Geselecteerde afbeelding", width=400)
    
    if st.button("Analyseer Groepen"):
        with st.spinner("AI analyseert de componenten..."):
            try:
                prompt = """
                Kijk naar deze foto van een elektrische verdeelkast. 
                Identificeer alle groepen. Maak een overzichtelijke tabel met:
                - Groepnummer
                - Component (bijv: B16, ALS)
                - Functie/Ruimte
                
                Eindig met een lege sectie 'Meetwaarden'.
                """
                
                # De eigenlijke aanroep naar de AI
                response = model.generate_content([prompt, img])
                
                st.success("Analyse voltooid!")
                st.markdown(response.text)
                st.download_button("Download Tekst", response.text, file_name="inspectie.txt")
            
            except Exception as e:
                st.error(f"Fout bij analyse: {e}")
                st.info("Tip: Controleer in Google AI Studio of je 'Gemini 1.5 Flash' kunt gebruiken.")
