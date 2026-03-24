import streamlit as st
import google.generativeai as genai
from PIL import Image

st.set_page_config(page_title="Elektra AI", layout="wide")
st.title("⚡ Elektra-Assistent - Model Zoeker")

# 1. API Key ophalen
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ Geen API Key gevonden in Secrets.")
    st.stop()

# 2. Vraag aan Google welke modellen JIJ mag gebruiken
beschikbare_modellen = []
try:
    for m in genai.list_models():
        # We zoeken alleen naar modellen die beelden en tekst kunnen verwerken
        if 'generateContent' in m.supported_generation_methods:
            beschikbare_modellen.append(m.name)
except Exception as e:
    st.error(f"Kan niet met Google verbinden. Fout: {e}")
    st.stop()

if not beschikbare_modellen:
    st.error("🚨 Jouw API-sleutel heeft geen toegang tot de benodigde modellen. Dit komt vaak door Europese regio-restricties of omdat er geen betaalmethode is gekoppeld in Google AI Studio.")
    st.stop()

st.success("Verbinding met Google gelukt! Kies hieronder een model uit de lijst:")

# 3. Laat jou kiezen uit de lijst die Google teruggeeft!
gekozen_model = st.selectbox("Selecteer een beschikbaar AI-model:", beschikbare_modellen)

# 4. De rest van de app
model = genai.GenerativeModel(gekozen_model)

bron = st.radio("Foto toevoegen via:", ["Camera", "Bladeren (Galerij)"])
if bron == "Camera":
    img_file = st.camera_input("Maak een foto")
else:
    img_file = st.file_uploader("Kies een afbeelding", type=['png', 'jpg', 'jpeg'])

if img_file is not None:
    img = Image.open(img_file)
    st.image(img, caption="Geselecteerde afbeelding", width=300)
    
    if st.button("Test dit model"):
        with st.spinner(f"Scannen met {gekozen_model}..."):
            try:
                prompt = "Maak een tabel van alle groepen op deze foto met Nummer, Type en Functie."
                response = model.generate_content([prompt, img])
                st.success("Gelukt! Dit model werkt voor jou.")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Fout met model {gekozen_model}: {e}")
                st.warning("Probeer een ander model uit de lijst hierboven!")
