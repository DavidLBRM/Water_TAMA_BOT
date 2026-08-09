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
    <style>
    body, [class*="css"] { direction: rtl; text-align: right; font-family: 'Segoe UI', Tahoma, sans-serif; }
    .stApp { background-color: #F8F9FA; }
    .stButton>button { border-radius: 4px !important; border: 1px solid #005A9C; background-color: #FFFFFF; color: #005A9C; font-weight: bold; transition: 0.3s; }
    .stButton>button:hover { background-color: #005A9C; color: white; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div { border-radius: 4px !important; border: 1px solid #DADCE0; background-color: #FFFFFF; }
    .stExpander { background-color: #FFFFFF; border-radius: 4px !important; border: 1px solid #DADCE0 !important; }
    .stChatMessage { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. אתחול מודל וטעינת נתונים (PDF + GIS)
# ==========================================
if "plan_name" not in st.session_state:
    st.session_state["plan_name"] = ""
if "plan_area" not in st.session_state:
    st.session_state["plan_area"] = 0.0
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# בלם חירום: בדיקה שמפתח ה-API קיים לפני שממשיכים
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("שגיאה: מפתח ה-API חסר. אנא הגדר GEMINI_API_KEY בהגדרות ה-Secrets של Streamlit.")
    st.stop()

@st.cache_resource(show_spinner="טוען מסמכי תמ\"א 1 למאגר הידע...")
def load_pdf_knowledge_base():
    uploaded_files = []
    kb_path = "knowledge_base"
    if os.path.exists(kb_path):
        for filename in os.listdir(kb_path):
            if filename.endswith(".pdf"):
                file_path = os.path.join(kb_path, filename)
                try:
                    g_file = genai.upload_file(path=file_path, display_name=filename)
                    while g_file.state.name == "PROCESSING":
                        time.sleep(2)
                        g_file = genai.get_file(g_file.name)
                    if g_file.state.name == "ACTIVE":
                        uploaded_files.append(g_file)
                except Exception as e:
                    st.error(f"שגיאה בהעלאת הקובץ {filename}: {e}")
    return uploaded_files

kb_files = load_pdf_knowledge_base()

# פונקציה לטעינת מספר שכבות GIS (Shapefiles)
@st.cache_data(show_spinner="טוען שכבות מידע גיאוגרפיות (רצועות תמ\"א 1)...")
def load_shapefiles():
    loaded_layers = {}
    try:
        import geopandas as gpd
        
        # מילון המקשר בין שם הקובץ באנגלית לשם שיוצג למשתמש במפה
        layers_info = {
            "afik_rashi": "אפיק נחל ראשי",
            "afik_mishni": "אפיק נחל משני",
            "nagar_rashi": "רצועת ניהול נגר (ראשי)",
            "nagar_mishni": "רצועת ניהול נגר (משני)",
            "hashpaa_rashi": "רצועת השפעה (ראשי)",
            "hashpaa_mishni": "רצועת השפעה (משני)",
            "hashpaa_darom_rahav": "השפעה נחל דרום רחב"
        }
        
        for file_key, layer_name in layers_info.items():
            shp_path = f"gis_data/{file_key}.shp"
            if os.path.exists(shp_path):
                # טעינת השכבה והמרת קואורדינטות לרשת העולמית לתצוגת אינטרנט
                gdf = gpd.read_file(shp_path)
                gdf = gdf.to_crs(epsg=4326)
                loaded_layers[layer_name] = gdf
                
        return loaded_layers
    except Exception as e:
        return {}

# טעינת שכבות ה-GIS בפועל
gis_data_dict = load_shapefiles()

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
    col_input, col_output = st.columns([1, 1.2])
    
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

    with col_output:
        st.subheader("שלב 2: סיכום ייעוץ והנחיות ניקוז (תמ\"א 1/8 + 1/7)")
        
        if st.button("הפק דוח ייעוץ", type="primary", use_container_width=True):
            with st.spinner("מנתח נתונים סטטוטוריים ומסמכי ידע..."):
                prompt_data = f"אנא הפק דוח ייעוץ סטטוטורי עבור התכנית '{st.session_state['plan_name']}' בשטח של {st.session_state['plan_area']} דונם, בהתאם להנחיות המערכת ולמסמכים המצורפים."
                response = model.generate_content([*kb_files, prompt_data])
                st.write(response.text)
        
        st.markdown("---")
        st.subheader("🗺️ תצוגה מרחבית (שכבות תמ\"א 1 ופשטי הצפה)")
        
        # בניית מפה עם תצלום אוויר (לוויין)
        m = folium.Map(location=[31.7683, 35.2137], zoom_start=7, tiles="CartoDB positron")
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='תצלום אוויר',
            overlay=False,
            control=True
        ).add_to(m)
        
        # הוספת כל שכבות ה-Shapefile למפה (אם הועלו בהצלחה לתיקיית gis_data)
        if gis_data_dict:
            # פלטת צבעים שונה לכל סוג רצועה להבחנה ויזואלית קלה
            colors = {
                "אפיק נחל ראשי": "#00008B",          # כחול כהה
                "אפיק נחל משני": "#1E90FF",          # כחול בהיר
                "רצועת ניהול נגר (ראשי)": "#006400", # ירוק כהה
                "רצועת ניהול נגר (משני)": "#32CD32", # ירוק בהיר
                "רצועת השפעה (ראשי)": "#8B0000",     # אדום כהה
                "רצועת השפעה (משני)": "#FF4500",     # כתום
                "השפעה נחל דרום רחב": "#DAA520"      # צהוב חרדל
            }
            
            for layer_name, gdf in gis_data_dict.items():
                layer_color = colors.get(layer_name, "#3388ff") # צבע ברירת מחדל
                
                # ציור הפוליגונים/קווים על המפה
                folium.GeoJson(
                    gdf,
                    name=layer_name,
                    style_function=lambda x, c=layer_color: {
                        'fillColor': c, 
                        'color': c, 
                        'weight': 2, 
                        'fillOpacity': 0.4
                    }
                ).add_to(m)
                
        # הוספת פאנל שליטה המאפשר לבודק להדליק ולכבות שכבות ספציפיות
        folium.LayerControl(collapsed=False).add_to(m)
        st_data = st_folium(m, height=450, use_container_width=True)

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
        
    if user_chat := st.chat_input("הקלד את שאלתך כאן... (למשל: מה ההנחיות לרוחב רצועת ניהול נגר בנחל משני?)"):
        st.chat_message("user").markdown(user_chat)
        st.session_state["chat_history"].append({"role": "user", "content": user_chat})
        
        with st.spinner("מחפש תשובה במסמכים הסטטוטוריים המצורפים..."):
            grounded_prompt = f"""
            אתה יועץ סטטוטורי. המשתמש שאל אותך שאלה.
            עליך לענות על השאלה אך ורק בהתבסס על המידע המופיע בקובצי ה-PDF המצורפים אליך (תמ"א 1, נספחי ניקוז וכו').
            
            חוקי ברזל למתן התשובה:
            1. אם התשובה נמצאת במסמכים, ענה עליה בצורה ברורה, מקצועית ומדויקת, וציין מאיזה מסמך או סעיף לקחת את המידע.
            2. אם המידע לא נמצא במפורש במסמכים המצורפים, אסור לך להמציא או לשער. עליך לענות במדויק: "מבדיקת המסמכים הסטטוטוריים שהוזנו למערכת, לא נמצאה התייחסות ישירה לנושא זה."
            
            השאלה של המשתמש: {user_chat}
            """
            try:
                res = model.generate_content([*kb_files, grounded_prompt])
                st.chat_message("assistant").markdown(res.text)
                st.session_state["chat_history"].append({"role": "assistant", "content": res.text})
            except Exception as e:
                st.error("אירעה שגיאה בעיבוד המסמכים. אנא נסה שוב.")

# ------------------------------------------
# כרטיסייה 3: אומדן יעדי נגר
# ------------------------------------------
with tab3:
    st.subheader("🧮 אומדן יעדי נגר ואיגום זמני (לפי מחשבון מינהל התכנון - תיקון 7/8)")
    st.markdown("> *כלי חישוב נפח הנגר לניהול בתכנית ובתכניות בשטח קטן מ 5 ד' גם לחישוב יעד איגום זמני ויעד ספיקה יוצאת מופחתת. המחשבון מתבסס על נתוני קרקע וגשם והמפורסם באתר מינהל התכנון...*")
    
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
