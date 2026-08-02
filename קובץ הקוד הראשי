import streamlit as st
import google.generativeai as genai

# 1. הגדרות העמוד
st.set_page_config(page_title="עוזר בודק תכניות - תמ\"א 1", layout="wide")

# 2. חיבור ל-API של גוגל (באמצעות המפתח הסודי שנגדיר בהמשך)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# 3. הגדרת הפרומפט המערכתי של המודל
system_instruction = """
הגדרת תפקיד:
אתה מומחה סטטוטורי ויועץ מקצועי לבודקי תכניות במינהל התכנון.
(הדבק לכאן את כל הפרומפט המלא והמשודרג שיצרנו קודם)
"""

# אתחול המודל
model = genai.GenerativeModel(
    model_name='gemini-1.5-pro',
    system_instruction=system_instruction
)

st.title("🏗️ מערכת תומכת החלטות - ניהול נגר (תיקון 7 לתמ\"א 1)")

# 4. יצירת הכרטיסיות בממשק
tab1, tab2, tab3 = st.tabs(["📄 ניתוח תכנית", "🧮 מחשבון יעדי נגר", "🗺️ מפת URBAN SIGHT"])

with tab1:
    st.header("הזנת נתוני תכנית לבדיקה")
    # כאן נוסיף בהמשך אופציה להעלאת קובץ PDF
    user_input = st.text_area("הזן את פרטי התכנית (שטח, תכסית, ייעוד, סמיכות לנחל):", height=150)
    
    if st.button("הפק דוח סטטוטורי"):
        if user_input:
            with st.spinner("מנתח את הנתונים..."):
                response = model.generate_content(user_input)
                st.write(response.text)
        else:
            st.warning("אנא הזן את נתוני התכנית לפני הפקת הדוח.")

with tab2:
    st.header("אומדן יעדי נגר")
    st.write("ממשק המחשבון בבנייה. כאן יופיעו שדות להזנת שטח, אזור גשם, סוג קרקע ותכסית.")

with tab3:
    st.header("בדיקה מרחבית")
    st.markdown("[לחץ כאן לפתיחת מערכת URBAN SIGHT בחלון חדש](הכנס_כאן_את_הלינק_שלכם)")
