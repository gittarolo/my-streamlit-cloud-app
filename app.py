import streamlit as st
import requests
import base64

# Oldal alapbeállításai
st.set_page_config(page_title="Saját Privát Tárhely", page_icon="🔒", layout="centered")


# 1. BIZTONSÁG: Jelszó ellenőrzése
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    st.title("🔒 Privát Tárhely Belépés")
    password_input = st.text_input("Kérlek, add meg a jelszót:", type="password")

    if st.button("Belépés"):
        # A jelszót a Streamlit Secrets-ből olvassuk be biztonságosan
        if password_input == st.secrets["ACCESS_PASSWORD"]:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("❌ Helytelen jelszó! Hozzáférés megtagadva.")
    return False


# Ha a jelszó helyes, betöltődik az app többi része
if check_password():
    st.title("📁 Saját Felhő Tárhely")
    st.info("Privát GitHub tárhely.")
    st.info("A Streamlit limitje 500mb-ra van állítva, de a GitHub 100mb-nál többet nem enged feltölteni.")

    # Környezeti változók beolvasása a biztonságos tárolóból
    TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO = st.secrets["GITHUB_REPO"]  # Formátum: "felhasznalonev/repo-neve"

    # --- FÁJL FELTÖLTÉS SECTION ---
    st.subheader("📤 Új fájl feltöltése")
    uploaded_file = st.file_uploader("Válassz ki egy fájlt a készülékedről:")

    if uploaded_file is not None:
        file_name = uploaded_file.name
        file_bytes = uploaded_file.read()

        # A GitHub API Base64 formátumban várja a fájlok tartalmát
        encoded_content = base64.b64encode(file_bytes).decode("utf-8")

        if st.button("🚀 Biztonságos feltöltés indítása"):
            with st.spinner("Fájl küldése a GitHubra..."):
                url = f"https://api.github.com/repos/{REPO}/contents/{file_name}"
                headers = {
                    "Authorization": f"token {TOKEN}",
                    "Accept": "application/vnd.github.v3+json"
                }
                data = {
                    "message": f"Feltöltve Streamlit-ről: {file_name}",
                    "content": encoded_content
                }

                # Küldés a GitHub API-nak
                response = requests.put(url, json=data, headers=headers)

                if response.status_code in [200, 201]:
                    st.success(f"✅ A(z) '{file_name}' sikeresen elmentve!")
                    st.rerun()
                else:
                    st.error(f"❌ Hiba történt: {response.json().get('message', 'Ismeretlen hiba')}")

    st.write("---")

    # --- FÁJL LISTÁZÁS, LETÖLTÉS ÉS TÖRLES SECTION ---
    st.subheader("📚 Tárolt fájljaid elérése")
    
    list_url = f"https://api.github.com/repos/{REPO}/contents/"
    
    with st.spinner("Fájllista frissítése..."):
        res = requests.get(list_url, headers=headers)
        
    if res.status_code == 200:
        files = res.json()
        valid_files = [f for f in files if f["type"] == "file"]
        
        if not valid_files:
            st.write("A tárhelyed jelenleg üres.")
        else:
            for f in valid_files:
                # Három oszlopra osztjuk a sort: Fájlnév, Letöltés gomb, Törlés gomb
                # Telefonos nézethez optimalizált arányok (col_delete kicsit kisebb)
                col_name, col_dl, col_del = st.columns([2, 1, 1])
                
                col_name.write(f"📄 {f['name']}")
                
                # 1. Letöltés gomb kezelése
                if col_dl.button("📥 Letölt", key=f"dl_btn_{f['sha']}"):
                    file_res = requests.get(f["url"], headers=headers)
                    if file_res.status_code == 200:
                        raw_data = base64.b64decode(file_res.json()["content"])
                        st.download_button(
                            label="💾 Mentés",
                            data=raw_data,
                            file_name=f["name"],
                            key=f"save_{f['sha']}"
                        )
                
                # 2. Törlés gomb kezelése
                if col_del.button("🗑️ Töröl", key=f"del_btn_{f['sha']}", type="secondary"):
                    with st.spinner("Törlés folyamatban..."):
                        delete_url = f"https://api.github.com/repos/{REPO}/contents/{f['name']}"
                        # A GitHub megköveteli az SHA azonosítót a törlés megerősítéséhez
                        delete_data = {
                            "message": f"Törölve Streamlit-ről: {f['name']}",
                            "sha": f["sha"]
                        }
                        
                        # A törléshez HTTP DELETE kérést kell küldeni
                        del_res = requests.delete(delete_url, json=delete_data, headers=headers)
                        
                        if del_res.status_code == 200:
                            st.success(f"🗑️ '{f['name']}' sikeresen törölve!")
                            st.rerun()  # Azonnali oldalfrissítés, hogy eltűnjön a listából
                        else:
                            st.error("❌ Nem sikerült törölni a fájlt.")
    else:
        st.error("Nem sikerült elérni a GitHub tárhelyet. Ellenőrizd a beállításokat!")