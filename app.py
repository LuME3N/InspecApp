import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# 1. App configuratie
st.set_page_config(page_title="Elektra-Assistent AI", page_icon="⚡")

# Gebruik de key die je hebt (In een echte app zetten we dit in 'Secrets')
genai.configure(api_key="JOUW_KEY_HIER") 
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("⚡ AI Verdeelkast Inspectie")
st.info("Maak een foto van de kast of het groepenschema voor een snelle rapportage.")

# 2. Camera of Upload
source = st.radio("Kies bron:", ["Camera", "Upload bestand"])
if source == "Camera":
    img_file = st.camera_input("Maak foto")
else:
    img_file = st.file_uploader("Kies afbeelding", type=['png', 'jpg', 'jpeg'])

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="Geselecteerde afbeelding", use_container_width=True)
    
    if st.button("Analyseer Groepen"):
        with st.spinner("Gemini AI analyseert de componenten..."):
            prompt = """
            Je bent een assistent voor een Nederlandse elektricien (NEN 1010). 
            Kijk naar deze foto en identificeer alle groepen in de verdeelkast.
            Maak een overzichtelijke tabel met:
            - Groepnummer
            - Component (bijv. Automaat, ALS, Krachtgroep)
            - Waarde (bijv. B16, C20)
            - Functie (indien leesbaar op de codering)
            
            Eindig met een sectie 'Meetwaarden' waar de elektricien later 
            isolatieweerstand en uitschakeltijden kan invullen.
            """
            
            response = model.generate_content([prompt, img])
            
            st.success("Analyse voltooid!")
            st.markdown(response.text)
            
            # Download knop voor tekst
            st.download_button("Download Rapport als Tekst", response.text, file_name="inspectie.txt")

st.divider()
st.caption("Ontwikkeld voor gebruik op de bouwplaats.")
