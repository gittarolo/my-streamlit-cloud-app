import streamlit as st
import requests
import base64
import mimetypes

# Oldal alapbeállításai
st.set_page_config(page_title="Saját Privát Tárhely", page_icon="🔒", layout="centered")

# jelszó ellenőrző függvény (maradt a régi)
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if st.session_state["authenticated"]:
        return True
    st.title("🔒 Privát Tárhely Belépés")
    password_input = st.text_input("Kérlek, add meg a jelszót:", type="password")
    if st.button("Belépés"):
        if password_input == st.secrets["ACCESS_PASSWORD"]:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("❌ Helytelen jelszó!")
    return False

if check_password():
    st.title("📁 Saját Felhő Tárhelyem")

    TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO = st.secrets["GITHUB_REPO"]
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}

    # --- FELTÖLTÉS SECTION ---
    st.subheader("📤 Új fájl feltöltése")
    uploaded_file = st.file_uploader("Válassz ki egy fájlt:")
    if uploaded_file is not None:
        file_name = uploaded_file.name
        if st.button("🚀 Biztonságos feltöltés indítása"):
            with st.spinner("Feltöltés..."):
                encoded_content = base64.b64encode(uploaded_file.read()).decode("utf-8")
                url = f"https://api.github.com/repos/{REPO}/contents/{file_name}"
                res = requests.put(url, json={"message": f"Feltöltve: {file_name}", "content": encoded_content}, headers=headers)
                if res.status_code in [200, 201]:
                    st.success("Sikeres feltöltés!")
                    st.rerun()
                else:
                    st.error("Hiba történt a feltöltésnél.")

    st.write("---")

    # --- LISTÁZÁS ÉS ELŐNÉZET SECTION ---
    st.subheader("📚 Tárolt fájljaid")
    
    # Inicializáljuk a memóriát az előnézethez és törléshez
    if "preview_sha" not in st.session_state: st.session_state["preview_sha"] = None
    if "delete_confirm_sha" not in st.session_state: st.session_state["delete_confirm_sha"] = None

    with st.spinner("Frissítés..."):
        res = requests.get(f"https://api.github.com/repos/{REPO}/contents/", headers=headers)
        
    if res.status_code == 200:
        valid_files = [f for f in res.json() if f["type"] == "file"]
        
        if not valid_files:
            st.write("A tárhely üres.")
        else:
            for f in valid_files:
                # 4 oszlop: Név, Előnézet, Letöltés, Törlés (telefonbarát elrendezés)
                col_name, col_prev, col_dl, col_del = st.columns([2, 1, 1, 1])
                col_name.write(f"📄 {f['name']}")
                
                # 1. ELŐNÉZET GOMB (Szem ikon)
                if col_prev.button("👁️", key=f"prev_btn_{f['sha']}", help="Előnézet"):
                    st.session_state["preview_sha"] = f["sha"] if st.session_state["preview_sha"] != f["sha"] else None
                    st.rerun()
                
                # 2. LETÖLTÉS GOMB
                if col_dl.button("📥", key=f"dl_btn_{f['sha']}", help="Letöltés"):
                    file_res = requests.get(f["url"], headers=headers)
                    if file_res.status_code == 200:
                        st.download_button(label="💾 Mentés", data=base64.b64decode(file_res.json()["content"]), file_name=f["name"], key=f"save_{f['sha']}")
                
                # 3. TÖRLES GOMB
                if col_del.button("🗑️", key=f"del_btn_{f['sha']}", help="Törlés"):
                    st.session_state["delete_confirm_sha"] = f["sha"]
                    st.rerun()

                # --- 👁️ AKTÍV ELŐNÉZET MEGJELENÍTÉSE ---
                if st.session_state["preview_sha"] == f["sha"]:
                    with st.expander("✨ Előnézet bezárása", expanded=True):
                        with st.spinner("Fájl betöltése az előnézethez..."):
                            file_res = requests.get(f["url"], headers=headers)
                            if file_res.status_code == 200:
                                raw_bytes = base64.b64decode(file_res.json()["content"])
                                filename_lower = f["name"].lower()
                                
                                # Képek megjelenítése
                                if filename_lower.endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                                    st.image(raw_bytes, use_container_width=True)
                                
                                # Videók lejátszása
                                elif filename_lower.endswith(('.mp4', '.mov', '.avi', '.webm')):
                                    st.video(raw_bytes)
                                
                                # Zenék / Hangfájlok lejátszása
                                elif filename_lower.endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                                    st.audio(raw_bytes)
                                
                                # PDF megjelenítése
                                elif filename_lower.endswith('.pdf'):
                                    base64_pdf = base64.b64encode(raw_bytes).decode('utf-8')
                                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
                                    st.markdown(pdf_display, unsafe_allow_html=True)
                                
                                # Minden más (Word, Excel stb.)
                                else:
                                    st.warning(f"A(z) '{f['name']}' fájlhoz nem érhető el közvetlen online előnézet (pl. Word/Excel). Kérlek, használd a letöltés gombot!")
                            else:
                                st.error("Nem sikerült letölteni a fájlt az előnézethez.")

                # --- 🗑️ AKTÍV TÖRLES MEGERŐSÍTÉSE ---
                if st.session_state["delete_confirm_sha"] == f["sha"]:
                    st.warning(f"⚠️ Biztosan törlöd: '{f['name']}'?")
                    c_yes, c_no = st.columns([1, 1])
                    if c_yes.button("🔥 Igen", key=f"y_{f['sha']}", type="primary"):
                        res = requests.delete(f"https://api.github.com/repos/{REPO}/contents/{f['name']}", json={"message": "Törölve", "sha": f["sha"]}, headers=headers)
                        if res.status_code == 200:
                            st.session_state["delete_confirm_sha"] = None
                            st.rerun()
                    if c_no.button("❌ Mégse", key=f"n_{f['sha']}"):
                        st.session_state["delete_confirm_sha"] = None
                        st.rerun()
                    st.write("---")
    else:
        st.error("Nem sikerült elérni a GitHub tárhelyet.")