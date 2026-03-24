import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import pandas as pd
import re
import io
import graphviz

# 1. Veilig de API Key ophalen
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ API Key niet gevonden in Secrets!")
    st.stop()

st.set_page_config(page_title="Scope 8 Pro", layout="wide", page_icon="⚡")
st.title("⚡ Scope 8 Keurmeester")

model = genai.GenerativeModel('models/gemini-2.5-flash')

bron = st.radio("Kies invoer:", ["Camera", "Bladeren (Galerij)"], horizontal=True)

if bron == "Camera":
    img_file = st.camera_input("Maak een foto van de groepenkast")
else:
    img_file = st.file_uploader("Kies een afbeelding", type=['png', 'jpg', 'jpeg'])

# Functie om de NEN1010 regels te checken
def controleer_metingen(df):
    beoordeling = []
    als_groepen_telling = {} 
    
    for index, row in df.iterrows():
        achter_als = str(row.get("Achter ALS", "")).strip()
        cat = str(row.get("Categorie", "")).upper()
        if "AUTOMAAT" in cat and achter_als and achter_als not in ["N.v.t.", "None", ""]:
            als_groepen_telling[achter_als] = als_groepen_telling.get(achter_als, 0) + 1

    for index, row in df.iterrows():
        fouten = []
        type_comp = str(row.get("Type", "")).upper()
        cat = str(row.get("Categorie", "")).upper()
        achter_als = str(row.get("Achter ALS", "")).strip()
        
        if "AUTOMAAT" in cat and achter_als in als_groepen_telling:
            if als_groepen_telling[achter_als] > 4:
                fouten.append(f">4 groepen op {achter_als}")

        for iso_col in ["R_iso L-N (MΩ)", "R_iso L-PE (MΩ)", "R_iso N-PE (MΩ)"]:
            r_iso = row.get(iso_col)
            if pd.notna(r_iso) and str(r_iso).strip() not in ["", "N.v.t.", "None"]:
                try:
                    if float(r_iso) < 1.0: fouten.append(f"{iso_col} te laag")
                except: pass
            
        if "AUTOMAAT" in cat:
            match = re.search(r'([BCDK])(\d+)', type_comp)
            if match:
                karakteristiek = match.group(1)
                i_nom = int(match.group(2))
                factor = 5 if karakteristiek == 'B' else 10 if karakteristiek == 'C' else 20 if karakteristiek == 'D' else 5
                i_a = factor * i_nom 
                max_zs = round(230 / i_a, 2) 

                z_s = row.get("Z_s (Ω)")
                if pd.notna(z_s) and str(z_s).strip() not in ["", "N.v.t.", "None"]:
                    try:
                        if float(z_s) > max_zs: fouten.append(f"Z_s > {max_zs}Ω")
                    except: pass
                    
                i_k = row.get("I_k (A)")
                if pd.notna(i_k) and str(i_k).strip() not in ["", "N.v.t.", "None"]:
                    try:
                        if float(i_k) < i_a: fouten.append(f"I_k < {i_a}A")
                    except: pass

        if "ALS" in cat or "AARDLEK" in cat:
            t_a = row.get("t_a (ms)")
            if pd.notna(t_a) and str(t_a).strip() not in ["", "N.v.t.", "None"]:
                try:
                    if float(t_a) > 300: fouten.append("t_a > 300ms")
                except: pass
                
            testknop = row.get("Testknop OK?")
            if testknop is False or str(testknop).upper() == "NEE":
                fouten.append("Testknop weigert")

        if not fouten:
            beoordeling.append("✅ Akkoord")
        else:
            beoordeling.append("❌ " + " | ".join(fouten))
            
    df["Beoordeling"] = beoordeling
    return df

# Functie om een visueel schema te tekenen
def teken_installatieschema(df):
    dot = graphviz.Digraph(comment='Verdeelkast')
    dot.attr(rankdir='TB') # Top to Bottom tekening
    
    hoofdschakelaar_naam = "Voeding (Binnenkomst)"
    dot.node(hoofdschakelaar_naam, hoofdschakelaar_naam, shape='box', style='filled', fillcolor='lightgrey')

    # Zoek of er een echte hoofdschakelaar in de tabel staat
    for _, row in df.iterrows():
        if "HOOFD" in str(row.get("Categorie", "")).upper():
            hoofdschakelaar_naam = str(row["Component"])
            dot.node(hoofdschakelaar_naam, f"{hoofdschakelaar_naam}\n{row.get('Type', '')}", shape='box', style='filled', fillcolor='lightgrey')
            dot.edge("Voeding (Binnenkomst)", hoofdschakelaar_naam) # Optioneel, verbind met bron

    for _, row in df.iterrows():
        comp = str(row.get("Component", "Onbekend"))
        cat = str(row.get("Categorie", "")).upper()
        achter = str(row.get("Achter ALS", "")).strip()
        type_val = str(row.get("Type", ""))
        functie = str(row.get("Functie", ""))
        
        if "ALS" in cat or "AARDLEK" in cat:
            dot.node(comp, f"{comp}\n{type_val}", shape='folder', style='filled', fillcolor='lightblue')
            dot.edge(hoofdschakelaar_naam, comp)
                
        elif "AUTOMAAT" in cat or "GROEP" in cat:
            naam_label = f"{comp}\n{type_val}"
            if functie and functie != "None":
                naam_label += f"\n({functie})"
            dot.node(comp, naam_label, shape='rect')
            
            # Koppel aan ALS of Hoofdschakelaar
            if achter and achter not in ["N.v.t.", "None", ""]:
                dot.edge(achter, comp)
            else:
                dot.edge(hoofdschakelaar_naam, comp)
                
    return dot

# De Analyse
if img_file is not None:
    img = Image.open(img_file)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(img, caption="Foto Verdeelkast", use_container_width=True)
    
    with col2:
        if st.button("Start AI Inspectie", type="primary"):
            with st.spinner("AI analyseert componenten en koppelingen..."):
                try:
                    prompt = """
                    Kijk naar deze foto van een verdeelkast.
                    Maak een lijst van alle componenten.
                    Geef het antwoord UITSLUITEND in puur JSON formaat (array van objecten).
                    Sleutels: "Component", "Type", "Categorie", "Achter ALS", "Functie".
                    Categorie MOET zijn: "Automaat", "ALS", of "Hoofdschakelaar".
                    "Achter ALS": Geef hier de EXACTE naam van de ALS waar deze automaat achter zit (bijv. "ALS 1"). Als het direct op de voeding zit, vul in "N.v.t.".
                    
                    Zorg dat er GEEN markdown omheen staat.
                    """
                    
                    response = model.generate_content([prompt, img])
                    ruwe_tekst = response.text.replace("```json", "").replace("```", "").strip()
                    groepen_data = json.loads(ruwe_tekst)
                    
                    for item in groepen_data:
                        cat = str(item.get("Categorie", "")).upper()
                        item["R_iso L-N (MΩ)"] = None
                        item["R_iso L-PE (MΩ)"] = None
                        item["R_iso N-PE (MΩ)"] = None
                        
                        if "ALS" in cat:
                            item["Z_s (Ω)"] = "N.v.t."
                            item["I_k (A)"] = "N.v.t."
                            item["t_a (ms)"] = None
                            item["Testknop OK?"] = False
                        elif "AUTOMAAT" in cat:
                            item["Z_s (Ω)"] = None
                            item["I_k (A)"] = None
                            item["t_a (ms)"] = "N.v.t."
                            item["Testknop OK?"] = "N.v.t."
                        else: 
                            item["Z_s (Ω)"] = "N.v.t."
                            item["I_k (A)"] = "N.v.t."
                            item["t_a (ms)"] = "N.v.t."
                            item["Testknop OK?"] = "N.v.t."
                    
                    st.session_state['meet_data'] = pd.DataFrame(groepen_data)
                    st.success("Tabel is klaar voor invoer!")
                    
                except Exception as e:
                    st.error(f"Fout bij het maken van de tabel: {e}")

        if 'meet_data' in st.session_state:
            st.write("### 📝 Invulformulier")
            
            bewerkte_df = st.data_editor(
                st.session_state['meet_data'],
                num_rows="dynamic",
                hide_index=True,
                use_container_width=True
            )
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("Voer NEN 1010 Controles uit", use_container_width=True):
                    gecontroleerde_df = controleer_metingen(bewerkte_df)
                    st.session_state['meet_data'] = gecontroleerde_df
                    st.rerun()
            
            with col_btn2:
                def to_excel(df):
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='Metingen')
                    return output.getvalue()
                    
                excel_data = to_excel(bewerkte_df)
                st.download_button("📥 Download als Excel", data=excel_data, file_name="meetrapport.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            
            st.divider()
            
            # Hier wordt het visuele schema getekend!
            st.write("### 📊 Visueel Installatieschema")
            schema = teken_installatieschema(st.session_state['meet_data'])
            st.graphviz_chart(schema)
