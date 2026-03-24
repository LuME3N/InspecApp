import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. Veilig de API Key ophalen
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ API Key niet gevonden! Check de Secrets in Streamlit.")
    st.stop()

# 2. App instellingen
st.set_page_config(page_title="Elektra AI", layout="wide", page_icon="⚡")
st.title("⚡ Elektra-Assistent")
st.write("Scan een verdeelkast en genereer direct een overzicht voor je rapportage.")

# 3. Het model dat we succesvol hebben getest!
model = genai.GenerativeModel('models/gemini-2.5-flash')

# 4. Interface voor de foto
bron = st.radio("Kies invoer:", ["Camera", "Bladeren (Galerij)"], horizontal=True)

if bron == "Camera":
    img_file = st.camera_input("Maak een foto van de groepenkast")
else:
    img_file = st.file_uploader("Kies een afbeelding", type=['png', 'jpg', 'jpeg'])

# 5. De Analyse
if img_file is not None:
    img = Image.open(img_file)
    st.image(img, caption="Geselecteerde kast", width=400)
    
    if st.button("Analyseer Groepen", type="primary"):
        with st.spinner("AI scant de componenten..."):
            try:
                # De opdracht aan de AI (Deze kun je later altijd nog aanpassen!)
                prompt = """
                Je bent een assistent voor een elektricien. 
                Kijk naar deze foto van een elektrische verdeelkast. 
                Identificeer alle groepen en componenten. Maak een overzichtelijke Markdown tabel met:
                - Groep / Positie (bijv: 1, 2, Hoofdschakelaar)
                - Component (bijv: Installatieautomaat, ALS, Krachtgroep)
                - Waarde/Karakteristiek (bijv: B16, C20, 40A/30mA)
                - Achter ALS (indien van toepassing)
                - Functie/Ruimte (Als er labels bijzitten)
                
                Eindig het rapport met een lege sectie 'Meetwaarden' (zoals Isolatieweerstand, Uitschakeltijd) die de elektricien later zelf kan invullen.
                """
                
                response = model.generate_content([prompt, img])
                
                if response.text:
                    st.success("✅ Analyse voltooid!")
                    st.markdown(response.text)
                    
                    # Download knop
                    st.download_button(
                        label="Download Rapport (Tekst)", 
                        data=response.text, 
                        file_name="verdeelkast_inspectie.txt",
                        mime="text/plain"
                    )
                else:
                    st.warning("De AI kon geen tekst genereren. Probeer een foto met beter licht.")
            
            except Exception as e:
                st.error(f"Er ging iets mis tijdens de analyse: {e}")
