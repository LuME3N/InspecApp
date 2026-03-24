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
st.set_page_config(page_title="Scope 8 Assistent", layout="wide", page_icon="⚡")
st.title("⚡ Scope 8 Meetrapport AI")
st.write("Scan de verdeelkast en genereer direct een meetformulier voor je keuring.")

# 3. Het 2.5 Flash model
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
    
    if st.button("Genereer Scope 8 Meetrapport", type="primary"):
        with st.spinner("AI bouwt het Scope 8 formulier op..."):
            try:
                # DE NIEUWE SCOPE 8 INSTRUCTIE VOOR DE AI
                prompt = """
                Je bent een expert NEN 3140 en SCIOS Scope 8 inspecteur. 
                Kijk naar deze foto van een elektrische verdeelkast en identificeer alle groepen en componenten.
                
                Genereer een professioneel meetrapport (in een Markdown Tabel) voor de inspectie.
                De tabel moet voor ELKE gevonden groep, aardlekschakelaar (ALS) of hoofdschakelaar een rij hebben met de volgende exacte kolommen:
                
                1. Component / Groep (bijv. Groep 1, ALS A, Hoofdschakelaar)
                2. Karakteristiek (bijv. B16, 40A/30mA, 40A)
                3. R-iso (MΩ)
                4. Z-s (Ω)
                5. ALS Uitschakeltijd (ms)
                6. ALS Uitschakelstroom (mA)
                7. R-A (Ω) [Aardverspreidingsweerstand]
                8. Testknop (OK / Niet OK)
                9. Opmerking / Functie
                
                Instructies voor het invullen:
                - Vul kolom 1, 2 en 9 in op basis van wat je op de foto ziet (of afleidt van de labels).
                - Vul in kolom 3 tot en met 8 stippellijntjes (.....) in. Dit is een leeg formulier dat de elektricien later zelf invult tijdens het meten.
                - Zorg dat alles in één overzichtelijke tabel staat.
                """
                
                response = model.generate_content([prompt, img])
                
                if response.text:
                    st.success("✅ Meetrapport gegenereerd!")
                    st.markdown(response.text)
                    
                    # Download knop
                    st.download_button(
                        label="Download Meetrapport (.txt)", 
                        data=response.text, 
                        file_name="scope8_meetrapport.txt",
                        mime="text/plain"
                    )
                else:
                    st.warning("De AI kon geen tekst genereren. Probeer een foto met beter licht.")
            
            except Exception as e:
                st.error(f"Er ging iets mis tijdens de analyse: {e}")
