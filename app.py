import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. Haal de API key veilig op uit de Secrets
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ API Key niet gevonden in Secrets! Voeg GEMINI_API_KEY toe in de Streamlit instellingen.")
    st.stop()

st.set_page_config(page_title="Elektra-Assistent", layout="wide")
st.title("⚡ ElektraVision AI")

# 2. Model selectie (we gebruiken 'gemini-1.5-flash' als standaard)
model = genai.GenerativeModel('gemini-1.5-flash')

img_file = st.camera_input("Maak een foto van de verdeelkast")

if img_file:
    img = Image.open(img_file)
    
    if st.button("Analyseer nu"):
        with st.spinner("Bezig met scannen..."):
            try:
                prompt = "Lijst alle groepen op deze foto op met hun type (bijv. B16) en functie."
                # We voegen een extra check toe voor de afbeelding
                response = model.generate_content([prompt, img])
                
                st.success("Klaar!")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Er ging iets mis: {e}")
                st.info("Tip: Controleer of je API-key nog geldig is in Google AI Studio.")
