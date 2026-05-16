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
    st.title("📁 Saját Felhő Tárhelyem")
    st.info("Ez a felület közvetlenül a privát GitHub tárhelyedhez kapcsolódik.")

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

    # --- FÁJL LISTÁZÁS ÉS LETÖLTÉS SECTION ---
    st.subheader("📚 Tárolt fájljaid elérése")

    list_url = f"https://api.github.com/repos/{REPO}/contents/"
    list_headers = {"Authorization": f"token {TOKEN}"}

    with st.spinner("Fájllista frissítése..."):
        res = requests.get(list_url, headers=list_headers)

    if res.status_code == 200:
        files = res.json()
        valid_files = [f for f in files if f["type"] == "file"]

        if not valid_files:
            st.write("A tárhelyed jelenleg üres.")
        else:
            for f in valid_files:
                # Sorok létrehozása a fájloknak és gomboknak
                col_name, col_btn = st.columns([3, 1])
                col_name.write(f"📄 {f['name']}")

                # Letöltés gomb kezelése
                if col_btn.button("Letöltés", key=f["sha"]):
                    # Privát repónál a nyers fájlt is csak tokennel tudjuk lekérni
                    file_res = requests.get(f["url"], headers=list_headers)
                    if file_res.status_code == 200:
                        raw_data = base64.b64decode(file_res.json()["content"])
                        st.download_button(
                            label="📥 Mentés a készülékre",
                            data=raw_data,
                            file_name=f["name"],
                            key=f"dl_{f['sha']}"
                        )
    else:
        st.error("Nem sikerült elérni a GitHub tárhelyet. Ellenőrizd a beállításokat!")