
import re
import unicodedata


FAQS = [
    {
        "intent": "greeting",
        "keywords": [
            "hello", "hi", "hey", "namaste", "namaskar",
            "hlo", "hii", "kaise ho"
        ],
        "en": (
            "Hello! Welcome to CivicPulse AI. I can help you "
            "understand complaint submission, tracking, categories "
            "and priority. What would you like help with?"
        ),
        "hi": (
            "Namaste! CivicPulse AI mein aapka swagat hai. "
            "Main complaint submit karne, status track karne, "
            "categories aur priority samajhne mein help kar sakta hoon. "
            "Aapko kya jaanna hai?"
        ),
    },
    {
        "intent": "submit_complaint",
        "keywords": [
            "submit complaint", "register complaint", "new complaint",
            "complaint kaise", "shikayat", "complaint darj",
            "complaint register", "report a problem"
        ],
        "en": (
            "To submit a complaint, sign in with your citizen account "
            "and open the complaint form on the home page. Enter your "
            "city, describe the issue clearly, and submit it. "
            "CivicPulse AI can predict a category and priority. "
            "Review the result shown by the website."
        ),
        "hi": (
            "Complaint submit karne ke liye citizen account se login "
            "karein. Home page par complaint form mein city aur problem "
            "ki details bharein, phir submit karein. System category "
            "aur priority predict karta hai. Website par dikhaya gaya "
            "result check kar lein."
        ),
    },
    {
        "intent": "track_complaint",
        "keywords": [
            "track complaint", "complaint status", "track my",
            "status check", "complaint id", "application status",
            "meri complaint", "status kaise", "shikayat status"
        ],
        "en": (
            "Open the Track Complaint page and enter the complaint ID "
            "shown after submission. The page will show the available "
            "status information. Keep your complaint ID safe."
        ),
        "hi": (
            "Track Complaint page kholiye aur complaint submit karne "
            "ke baad mili complaint ID enter kijiye. Page par available "
            "status dikh jayega. Apni complaint ID sambhal kar rakhein."
        ),
    },
    {
        "intent": "categories",
        "keywords": [
            "category", "categories", "complaint type",
            "water issue", "garbage", "road issue", "street light",
            "drainage", "kis category", "kaunsi category"
        ],
        "en": (
            "CivicPulse AI uses its trained model to predict a complaint "
            "category from the description. Describe the issue clearly "
            "—for example, water supply interruption, garbage on a road, "
            "or a damaged road. The prediction is automated and may "
            "need human review."
        ),
        "hi": (
            "CivicPulse AI complaint ki description se category predict "
            "karta hai. Problem clearly likhein—jaise paani nahi aana, "
            "road par kachra, ya sadak damage hona. Prediction automated "
            "hai, isliye zaroorat padne par human review hona chahiye."
        ),
    },
    {
        "intent": "priority",
        "keywords": [
            "priority", "urgent", "emergency", "high priority",
            "priority kaise", "urgent complaint", "kitni jaldi"
        ],
        "en": (
            "CivicPulse AI estimates complaint priority using its "
            "priority rules. A high priority label is not a guarantee "
            "of immediate municipal action. For an immediate danger "
            "or emergency, contact the appropriate local emergency "
            "service directly."
        ),
        "hi": (
            "CivicPulse AI apne priority rules se complaint ki priority "
            "estimate karta hai. High priority ka matlab immediate "
            "action ki guarantee nahi hai. Agar turant khatra ya "
            "emergency ho, toh relevant local emergency service se "
            "seedha sampark karein."
        ),
    },
    {
        "intent": "login",
        "keywords": [
            "login", "log in", "sign in", "account", "signup",
            "sign up", "register account", "citizen account",
            "login nahi", "login problem"
        ],
        "en": (
            "Citizens should use the citizen login or sign-up page. "
            "The admin login is intended for authorized administrators. "
            "If login fails, check your credentials and use the correct "
            "login page."
        ),
        "hi": (
            "Citizens citizen login ya sign-up page use karein. Admin "
            "login sirf authorized administrators ke liye hai. Login "
            "nahi ho raha ho toh credentials check karein aur sahi "
            "login page use karein."
        ),
    },
    {
        "intent": "thanks",
        "keywords": [
            "thanks", "thank you", "thankyou", "shukriya",
            "dhanyawad", "thank u"
        ],
        "en": (
            "You're welcome! I'm here to help with CivicPulse AI."
        ),
        "hi": (
            "Aapka swagat hai! CivicPulse AI ke baare mein aur kuch "
            "poochna ho toh zaroor poochhein."
        ),
    },
]


def normalize_text(text):
    text = unicodedata.normalize("NFKC", text.lower())
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def detect_language(text):
    hindi_words = {
        "hai", "hain", "kaise", "kya", "meri", "mera", "mujhe",
        "chahiye", "karna", "karo", "nahi", "nahin", "paani",
        "pani", "sadak", "kachra", "shikayat", "batao", "kaise"
    }

    words = set(normalize_text(text).split())

    if words.intersection(hindi_words):
        return "hi"

    return "en"


def get_faq_response(message):
    cleaned = normalize_text(message)
    language = detect_language(message)

    if not cleaned:
        return {
            "reply": (
                "Please type a question."
                if language == "en"
                else "Kripya apna sawaal type karein."
            ),
            "intent": "empty",
            "source": "faq",
        }

    for item in FAQS:
        for keyword in item["keywords"]:
            keyword_clean = normalize_text(keyword)

            if (
                keyword_clean in cleaned.split()
                if len(keyword_clean) <= 3
                else keyword_clean in cleaned
            ):
                return {
                    "reply": item[language],
                    "intent": item["intent"],
                    "source": "faq",
                }


    if language == "hi":
        reply = (
            "Mujhe is sawaal ka exact jawab abhi nahi pata. "
            "Aap complaint submit karne, status track karne, "
            "category, priority ya login ke baare mein pooch sakte hain."
        )
    else:
        reply = (
            "I don't have an exact answer for that yet. You can ask "
            "me about submitting a complaint, tracking its status, "
            "categories, priority, or login."
        )

    return {
        "reply": reply,
        "intent": "fallback",
        "source": "faq",
    }
