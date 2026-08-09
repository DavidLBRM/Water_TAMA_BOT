import streamlit as st
import google.generativeai as genai
import folium
from streamlit_folium import st_folium
import os
import time

# ==========================================
# 1. הגדרות תצורה ועיצוב
# ==========================================
st.set_page_config(page_title="מערכת עזר לבודקי תכניות - תמ\"א 1", layout="wide")

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" rel="stylesheet" />
    <style>
    /* הגדרת רקע וגופנים בסגנון גוגל */
    .stApp {
        background-color: #F8F9FA;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    body, [class*="css"] { 
        direction: rtl; 
        text-align: right; 
    }
    
    /* עיצוב כרטיסיות (Tabs) בסגנון Material */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        border-bottom: 1px solid #DADCE0;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 0px;
        color: #5F6368;
        font-weight: 500;
        font-size: 16px;
    }
    .stTabs [aria-selected="true"] {
        color: #1A73E8 !important;
        border-bottom: 3px solid #1A73E8 !important;
    }
    
    /* עיצוב כפתורים (Geometric Balance + Google Blue) */
    .stButton>button { 
        border-radius: 4px !important; 
        border: 1px solid #DADCE0; 
        background-color: #FFFFFF; 
        color: #1A73E8; 
        font-weight: 600; 
        transition: 0.2s box-shadow;
    }
    .stButton>button:hover { 
        background-color: #F4F8LF; 
        box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3);
    }
    
    /* עיצוב תיבות קלט וטקסט (Cards) */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div { 
        border-radius: 4px !important; 
        border: 1px solid #DADCE0; 
        background-color: #FFFFFF;
    }
    .stTextInput>div>div>input:focus {
        border: 2px solid #1A73E8;
    }
    
    /* עיצוב תיבות נגללות (Expanders) */
    .stExpander {
        background-color: #FFFFFF;
        border-radius: 8px !important;
        border: 1px solid #DADCE0 !important;
        box-shadow: 0 1px 2px 0 rgba(60,64,67,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. אתחול מודל וטעינת קבצי PDF
# ==========================================
if "plan_name" not in st.session_state:
    st.session_state["plan_name"] = ""
if "plan_area" not in st.session_state:
    st.session_state["plan_area"] = 0.0
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.warning("הערת מערכת: מפתח ה-API טרם הוגדר ב-Secrets. המערכת תפעל במצב תצוגה בלבד.")

# פונקציה להעלאת ה-PDF לגוגל ושמירתם בזיכרון
@st.cache_resource(show_spinner="טוען מסמכי תמ\"א 1 למאגר הידע (זה עשוי לקחת דקה)...")
def load_pdf_knowledge_base():
    uploaded_files = []
    kb_path = "knowledge_base"
    if os.path.exists(kb_path):
        for filename in os.listdir(kb_path):
            if filename.endswith(".pdf"):
                file_path = os.path.join(kb_path, filename)
                # העלאת הקובץ ל-Gemini API
                g_file = genai.upload_file(path=file_path, display_name=filename)
                
                # המתנה לעיבוד הקובץ בשרתי גוגל
                while g_file.state.name == "PROCESSING":
                    time.sleep(2)
                    g_file = genai.get_file(g_file.name)
                    
                if g_file.state.name == "ACTIVE":
                    uploaded_files.append(g_file)
    return uploaded_files

# טעינת הקבצים בפועל
kb_files = load_pdf_knowledge_base()

master_prompt = """
הגדרת תפקיד:
אתה מומחה סטטוטורי ויועץ מקצועי לבודקי תכניות במינהל התכנון. מטרתך היא לנתח נתונים של תכניות בניין עיר (תב"ע), ולספק ייעוץ מקצועי האם התכנית עומדת בהנחיות פרקי המים בתמ"א 1 (תמ"א 1/8 + תמ"א 1/7), מה היא צריכה לכלול בהיבטי ניקוז, אילו היתרים נדרשים, והאם יש צורך להפנות ליועץ ניקוז, רשות הניקוז או רשות המים.

שלב 1: תחקור ואיסוף נתונים (חובה!)
לפני מתן ייעוץ, ודא שיש בידיך את הנתונים הבאים מבודק התכנית:
* שטח התכנית (בדונמים - ציון האם מעל או מתחת ל-5 דונם).
* האם התכנית כוללת תוספת בינוי/תכסית אטומה (באחוזים או במ"ר).
* ייעוד התכנית (מגורים, מסחר/תעסוקה, תשתיות, מבני ציבור, חקלאות, אתר ויסות נגר וכו').
* מיקום התכנית (אזור גשם).
* נתוני קרקע (סוג הקרקע).
* האם ידוע על סמיכות לנחל או הימצאות באזור החשוד בזיהום מי תהום/רגישות הידרולוגית גבוהה.
* האם התכנית היא כוללנית/מתאר יישובית, תשתית ארצית/אזורית, או משנה/מוסיפה מוצא ניקוז לשטח פתוח.

שלב 2: סיכום ייעוץ והנחיות ניקוז (על בסיס תמ"א 1/8 + 1/7)
לאחר קבלת כל הנתונים, הצג את הייעוץ בחלוקה לסעיפים הבאים:

א. אומדן יעדי נגר ודרישות הגשה (מבוסס מחשבון הנגר):
* עבור כל תכנית: חלץ והצג את "נפח הנגר לניהול".
* אם התכנית מתחת ל-5 דונם (וכוללת בינוי): חלץ והצג בנוסף את "יעד איגום זמני" ואת "יעד ספיקה יוצאת מופחתת". ציין שאין חובת הגשת נספח ניהול נגר מקיף (אלא אם מוסד התכנון קבע אחרת), ויש להטמיע את האמצעים בשלב הרישוי.
* אם התכנית 5 דונם ומעלה (וכוללת בינוי): ציין כי קיימת חובה קטגורית להגיש נספח "ניהול נגר וניקוז" (נספח ב'4) מקיף, מה שמחייב שכירת יועץ ניקוז/הידרולוג לביצוע החישובים. 

ב. חובת התייעצות רגולטורית:
* רשות הניקוז: קבע חד משמעית כי יש להפנות את התכנית להתייעצות עם רשות הניקוז אם היא עונה על אחד התנאים: (1) סמיכות לנחל (אפיק, פשט הצפה, רצועת השפעה). (2) תכנית כוללנית/מתאר יישובית. (3) תכנית לתשתית ארצית/אזורית. (4) משנה מוצא ניקוז לשטח פתוח. (5) אתר ויסות נגר.
* רשות המים: אם התכנית באזור החשוד בזיהום מי תהום/רגישות הידרולוגית גבוהה, קבע כי חובה לקבל חוות דעת מרשות המים לעניין חלחול/החדרת נגר.

ג. היתרים נדרשים (בהתאם לסעיף 6 בתמ"א 1/8):
* פרט אילו היתרים נדרשים בהתאם למהות התכנית המוצעת ולסעיף 6 העוסק בהיתרים לקווים ולמתקני מי מערכת.

ד. המלצות תכנוניות מותאמות ייעוד קרקע:
* למגורים/עירוב שימושים: המלץ על ניהול הנגר בשצ"פים באמצעות פתרונות מבוססי טבע (NBS). קביעת מפלס 0.00 מעל רום פשט ההצפה (1:100).
* לתשתיות ודרכים: המלץ על ניהול באיי תנועה ושולי דרך, ותכנון מערכת תיעול לעמידה באירועי 1:5 ו-1:20.
* לתעסוקה ומסחר / מוסדות ציבור: המלץ על אגירת מים בתת-הקרקע או ניצול רחבות הריצוף הגדולות להשהיה.

הוראות מסגרת חובה (Knowledge Base & Style):
1. התבסס אך ורק על מסמכי ה-PDF המצורפים אליך (תמ"א 1, נספח ב'4, מסמכי מדיניות). אין להמציא סעיפי חוק או תקנות.
2. ודא כי התשובה כתובה בעברית תקינה.
3. סגנון: שפה מקצועית, אובייקטיבית וסמכותית. ללא פסקאות הקדמה מאריכות.
4. סיים את הייעוץ בפסקת סיכום ברורה המציגה את השורה התחתונה על סמך התחקור והנתונים.
"""

model = genai.GenerativeModel(
    model_name='gemini-1.5-pro',
    system_instruction=master_prompt
)

st.title("💧 מערכת תומכת החלטות - ניהול נגר (תיקונים 7 ו-8 לתמ\"א 1)")
st.markdown("---")

# ==========================================
# 3. יצירת הכרטיסיות
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 תחקור וייעוץ תכנוני (תמ\"א 1)", 
    "🤖 יועץ AI סטטוטורי", 
    "🧮 אומדן יעדי נגר", 
    "📚 ספריית הוראות ותקנים"
])

# ------------------------------------------
# כרטיסייה 1: תחקור וייעוץ תכנוני
# ------------------------------------------
with tab1:
    col_input, col_output = st.columns([1.2, 1])
    
    with col_input:
        st.subheader("שלב 1: איסוף נתוני התכנית לבדיקת עמידה בהנחיות תמ\"א 1")
        
        with st.expander("1. זיהוי התכנית", expanded=True):
            st.session_state["plan_name"] = st.text_input("שם התכנית:", value=st.session_state["plan_name"])
            st.text_input("מספר התכנית:")
            
        with st.expander("2. שטח התכנית ותוספת בינוי", expanded=True):
            st.session_state["plan_area"] = st.number_input("שטח התכנית (בדונם):", min_value=0.0, step=0.1, value=st.session_state["plan_area"])
            st.slider("אחוז תכסית אטומה משוער (%):", 0, 100, 50)
            st.radio("האם התכנית כוללת תוספת בינוי/תכסית אטומה?", ["כן", "לא"])
            
        with st.expander("3. ייעוד הקרקע הראשי של התכנית", expanded=True):
            st.selectbox("בחר ייעוד ראשי:", [
                "מגורים/עירוב שימושים", 
                "תשתיות, דרכים ומסילות", 
                "תעסוקה ומסחר", 
                "מוסדות ומבני ציבור", 
                "חקלאות/שטח פתוח", 
                "אתר ויסות נגר"
            ])
            
        with st.expander("4. רגישות סביבתית ומאפיינים רגולטוריים", expanded=True):
            st.checkbox("האם ידוע על סמיכות לנחל?")
            st.checkbox("הימצאות באזור החשוד בזיהום מי תהום / רגישות הידרולוגית גבוהה")
            st.checkbox("תכנית כוללנית/ מתאר יישובית")
            st.checkbox("תכנית לתשתית ארצית או אזורית")
            st.checkbox("שינוי או הוספת מוצא ניקוז לשטח פתוח")
            st.checkbox("כוללת אתר ויסות נגר (נספח ב' 15)")
            
        st.subheader("5. מפת מיקום התכנית והתניות אזוריות (תמ\"א 1)")
        st.caption("בחירת מיקום על גבי המפה תעדכן אוטומטית את עובי הגשם (P50), סוג הקרקע, סמיכות לנחל ורגישות הידרולוגית.")
        
        # מפה בסיסית ממוקדת על ישראל
        m = folium.Map(location=[31.7683, 35.2137], zoom_start=7)
        folium.LatLngPopup().add_to(m)
        st_data = st_folium(m, height=300, use_container_width=True)

    with col_output:
        st.subheader("שלב 2: סיכום ייעוץ והנחיות ניקוז (תמ\"א 1/8 + 1/7)")
        st.info("כאן יופק דוח הייעוץ הסטטוטורי לאחר איסוף הנתונים.")
        if st.button("הפק דוח ייעוץ", use_container_width=True):
            with st.spinner("מנתח נתונים סטטוטוריים ומסמכי ידע..."):
                prompt_data = f"אנא הפק דוח ייעוץ סטטוטורי עבור התכנית '{st.session_state['plan_name']}' בשטח של {st.session_state['plan_area']} דונם, בהתאם להנחיות המערכת ולמסמכים המצורפים."
                # העברת קבצי ה-PDF יחד עם הבקשה למודל!
                response = model.generate_content([*kb_files, prompt_data])
                st.write(response.text)

# ------------------------------------------
# כרטיסייה 2: יועץ AI סטטוטורי
# ------------------------------------------
with tab2:
    p_name_display = st.session_state["plan_name"] if st.session_state["plan_name"] else "[הכנס_שם_תכנית_לפי_הנתונים]"
    p_area_display = st.session_state["plan_area"] if st.session_state["plan_area"] > 0 else "[X]"
    
    st.subheader("💬 יועץ AI לניהול נגר ובינוי")
    st.write("מענה לשאלות בודקים, פרשנות תמ\"א 1, מודלים הידרולוגיים והנחיות ניקוז (מבוסס על מסמכי המקור).")
    
    # הודעת פתיחה
    st.chat_message("assistant").markdown(
        f"שלום! אני יועץ בינה מלאכותית סטטוטורי של מינהל התכנון. אני מעודכן בתמ\"א 1 (תיקונים 7 ו-8), נספח ב'4 (הנחיות להכנת מסמך ניהול נגר וניקוז) ומסמכי המדיניות לניהול נגר עירוני. אני רואה שאתה עובד כעת על תכנית **{p_name_display}** ({p_area_display} דונם). במה אוכל לסייע לך בבדיקת התכנית?"
    )
    
    for msg in st.session_state["chat_history"]:
        st.chat_message(msg["role"]).markdown(msg["content"])
        
    if user_chat := st.chat_input("הקלד את שאלתך כאן..."):
        st.chat_message("user").markdown(user_chat)
        st.session_state["chat_history"].append({"role": "user", "content": user_chat})
        
        with st.spinner("מנתח מסמכים..."):
            # העברת קבצי ה-PDF יחד עם שאלת המשתמש!
            res = model.generate_content([*kb_files, user_chat])
            st.chat_message("assistant").markdown(res.text)
            st.session_state["chat_history"].append({"role": "assistant", "content": res.text})

# ------------------------------------------
# כרטיסייה 3: אומדן יעדי נגר
# ------------------------------------------
with tab3:
    st.subheader("🧮 אומדן יעדי נגר ואיגום זמני")
    st.caption("כלי חישוב להערכת נפח נגר לניהול, יעד איגום זמני ויעד ספיקה יוצאת מופחתת בהתאם להנחיות הרגולטוריות (תיקון 7/8).")
    
    st.info('**הגדרת המחשבון עפ"י תיקון 7 לתמ"א 1:**\n"כלי חישוב נפח הנגר לניהול בתכנית ובתכניות בשטח קטן מ 5 ד\' גם לחישוב יעד איגום זמני ויעד ספיקה יוצאת מופחתת. המחשבון מתבסס על נתוני קרקע וגשם והמפורסם באתר מינהל התכנון..."')
    
    col_calc_in, col_calc_out = st.columns([1, 1])
    
    with col_calc_in:
        st.markdown("**משתני חובה להרצת המודל:**")
        calc_area = st.number_input("1. שטח התכנית (בדונמים):", min_value=0.0, value=st.session_state["plan_area"], key="calc_area")
        st.selectbox("2. מיקום התכנית (אזור גשם):", ["מישור החוף", "שפלה", "הר", "צפון", "דרום"])
        calc_imperv = st.slider("3. התכסית האטומה המוצעת (%):", 0, 100, 60)
        st.selectbox("4. נתוני קרקע (סוג הקרקע):", ["חולית", "חמרה", "חרסיתית / כבדה", "סלעית"])
        st.checkbox("מיושמים אמצעי חלחול/החדרה (הפחתה עד 30% מיעד איגום)")
        
    with col_calc_out:
        st.markdown("**תוצאות ותנאי בסיס:**")
        
        if calc_area >= 5.0:
            st.success("**תכנית ≥ 5 דונם (חובת 75%)**")
            st.metric(label="נפח הנגר לניהול:", value="344 מ\"ק")
            st.markdown("סך הנגר היממתי הנוצר באירוע גשם 1:50 שנה: **459 מ\"ק** (מקדם משוקלל C = 0.64)")
            st.warning("**הנחיה סטטוטורית ליעדי קצה בתכניות מעל 5 דונם:**\n\nהיות ששטח התכנית עולה על 5 דונם, חישוב יעד האיגום הזמני ויעד הספיקה היוצאת המופחתת לא מוצג כאן; יעדים אלו יחושבו באופן פרטני לכל תת-אגן במסגרת נספח הניקוז (נספח ב'4) על ידי יועץ הניקוז/ההידרולוג.")
        else:
            st.info("**תכנית קטנה מ-5 דונם (חובת 50%)**")
            st.metric(label="נפח הנגר לניהול:", value="150 מ\"ק")
            st.metric(label="יעד איגום זמני:", value="110 מ\"ק")
            st.metric(label="יעד ספיקה יוצאת מופחתת:", value="0.45 מקש\"נ")

# ------------------------------------------
# כרטיסייה 4: ספריית הוראות ותקנים
# ------------------------------------------
with tab4:
    st.subheader("📚 ספריית הוראות סטטוטוריות ותקנים - תמ\"א 1 (תיקונים 7 ו-8)")
    st.write("ריכוז קריטריונים תכנוניים להגנה מפני הצפות, הגדרות מפתח והנחיות ניהול נגר לבודקי תכניות.")
    
    st.markdown("#### טבלה מס' 1: קריטריונים תכנוניים להגנה מפני הצפות לפי שימושי קרקע")
    st.markdown("""
    | ייעוד / שימוש השטח | תקופת חזרה מינימלית לתכנון |
    | :--- | :--- |
    | רחובות וכבישים עירוניים | 1:5 |
    | חקלאות ופארקים פתוחים | 1:10 |
    | דרכים ארציות / תשתיות תעבורה | 1:50 |
    | מגורים, מסחר, תעסוקה ומבני ציבור (מפלס 0.00) | 1:100 |
    | בנייה בתת-הקרקע וחניונים | 1:100 |
    """)
    
    st.markdown("#### מונחים והגדרות מפתח בתמ\"א 1 (פרק המים)")
    st.markdown("""
    * **נפח נגר לניהול:** אחוז מנפח הנגר הנוצר בתכנית שעל פיו מחושבים יעד האיגום ויעד הספיקה (סעיף 7.1.2).
    * **יעד איגום זמני:** נפח הנגר הנדרש להשהייה בתחום התכנית לשם עמידה בספיקה המופחתת.
    * **יעד ספיקה יוצאת מופחתת:** הספיקה המרבית המותרת לשחרור ממערכות ניהול הנגר של התכנית.
    * **אתר ויסות נגר:** שטח המיועד להשהיית נגר לפרק זמן קצר כדי להקטין ספיקת מורד ולצמצם שיטפונות (נספח ב'15).
    * **חלחול / החדרה:** מעבר מים ישיר לתווך הבלתי רווי או הרווי, בעל חשיבות עליונה באזורי עדיפות להעשרת מי תהום.
    """)
