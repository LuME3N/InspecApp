import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. Veilig de API Key ophalen uit Streamlit Secrets
try:
    # Zorg dat je GEMINI_API_KEY = "jouw_key" hebt staan in je Streamlit Secrets!
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ API Key niet gevonden in Secrets! Voeg GEMINI_API_KEY toe in de Streamlit instellingen.")
    st.stop()

# 2. App instellingen
st.set_page_config(page_title="ElektraVision AI", layout="wide")
st.title("⚡ Elektra-Assistent AI")

# 3. Model selectie
model = genai.GenerativeModel('gemini-1.5-flash')

# 4. De Keuzeknop voor Foto-bron (Deel 1 van de aanpassing)
bron = st.radio("Kies hoe je de foto wilt toevoegen:", ["Camera", "Bladeren (Galerij/Upload)"])

# 5. Het input veld (Deel 2 van de aanpassing)
img_file = None # Begin met niets
if bron == "Camera":
    img_file = st.camera_input("Maak een foto van de verdeelkast")
else:
    img_file = st.file_uploader("Kies een afbeelding", type=['png', 'jpg', 'jpeg'])

# 6. De analyse uitvoeren
if img_file is not None:
    # Toon de geselecteerde afbeelding
    img = Image.open(img_file)
    st.image(img, caption="Geselecteerde afbeelding", width=400)
    
    # Een aparte knop om de AI te starten (zodat het niet direct begint)
    if st.button("Analyseer Groepen"):
        with st.spinner("AI analyseert de componenten..."):
            try:
                # De verbeterde prompt voor Gemini
                prompt = """
                Kijk naar deze foto van een elektrische verdeelkast. 
                Identificeer alle groepen. Maak een overzichtelijke tabel met:
                - Groepnummer (bijv: 1, A1, I)
                - Type component (bijv: Installatieautomaat, ALS, Fornuisgroep)
                - Waarde (bijv: B16, C20, B20)
                - Gekoppeld aan ALS (indien leesbaar, bijv: ALS A)
                
                Eindig met een lege sectie 'Meetwaarden' voor later gebruik.
                """
                
                # Gemini analyseert de afbeelding
                response = model.generate_content([prompt, img])
                
                st.success("Analyse voltooid!")
                st.markdown(response.text)
                
                # Download knop voor de resultaten
                st.download_button("Download Tekst", response.text, file_name="inspectie.txt")
            
            except Exception as e:
                st.error(f"Er ging iets mis met de AI: {e}")
                st.info("Tip: Controleer of je foto duidelijk is en of je API-key nog geldig is.")

else:
    st.info("👈 Voeg eerst een foto toe met de camera of via bladeren.")
