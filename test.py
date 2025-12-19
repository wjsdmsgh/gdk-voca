import streamlit as st
import json, os
from openai import OpenAI

st.set_page_config(page_title="AI 영어 단어장", layout="centered")

DATA_FILE = "voca.json"
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ================= DB =================
def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

voca_db = load_db()

# ================= 상태 =================
if "page" not in st.session_state:
    st.session_state.page = "home"

if "current_session" not in st.session_state:
    st.session_state.current_session = None

if "quiz" not in st.session_state:
    st.session_state.quiz = {
        "list": [],
        "wrong": [],
        "idx": 0,
        "correct": 0,
        "dir": "EN_KO"
    }

# ================= 홈 =================
def home():
    st.title("📚 단어장 선택")

    with st.form("session_form"):
        name = st.text_input(
            "회차",
            autofocus=True,
            label_visibility="collapsed"
        )
        submitted = st.form_submit_button("생성")

    if submitted and name.strip():
        voca_db.setdefault(name.strip(), [])
        save_db(voca_db)
        st.session_state.current_session = name.strip()
        st.session_state.page = "vocab"
        st.rerun()

    st.divider()
    for s in voca_db:
        if st.button(s):
            st.session_state.current_session = s
            st.session_state.page = "vocab"
            st.rerun()

# ================= 단어장 =================
def vocab_page():
    s = st.session_state.current_session
    st.title(f"📘 {s}")

    if st.button("⬅ 회차 선택"):
        st.session_state.page = "home"
        st.rerun()

    # ---------- 단어 추가 ----------
    with st.form("add_word"):
        word = st.text_input(
            "영어 단어",
            autofocus=True
        )
        mean = st.text_input("뜻 (/로 구분)")
        submitted = st.form_submit_button("추가")

    if submitted and word.strip():
        ai_mean = client.responses.create(
            model="gpt-4.1-mini",
            input=f"영어 단어 '{word}'의 가장 많이 쓰이는 한국어 뜻을 /로 구분해서 알려줘."
        ).output_text.strip()

        final = "/".join(set(mean.split("/")) | set(ai_mean.split("/")))

        voca_db[s].append({
            "word": word.strip(),
            "mean": final,
            "wrong": 0
        })
        save_db(voca_db)
        st.rerun()

    st.divider()
    st.subheader("📋 단어 목록")

    # ---------- 단어 목록 + 뜻 수정 ----------
    for i, v in enumerate(voca_db[s]):
        col1, col2 = st.columns([3, 1])

        with col1:
            new_mean = st.text_input(
                v["word"],
                value=v["mean"],
                key=f"mean_{i}"
            )
            if new_mean != v["mean"]:
                v["mean"] = new_mean
                save_db(voca_db)

        with col2:
            if st.button("❌", key=f"del_{i}"):
                voca_db[s].remove(v)
                save_db(voca_db)
                st.rerun()

    st.divider()
    if st.button("▶ 퀴즈 시작"):
        q = st.session_state.quiz
        q["list"] = sorted(voca_db[s], key=lambda x: -x["wrong"])
        q["wrong"] = []
        q["idx"] = 0
        q["correct"] = 0
        q["dir"] = "EN_KO"
        st.session_state.page = "quiz"
        st.rerun()

# ================= 퀴즈 =================
def quiz_page():
    q = st.session_state.quiz
    lst = q["list"]

    if q["idx"] >= len(lst):
        st.title("🏁 퀴즈 종료")
        st.write(f"{len(lst)}문제 중 {q['correct']}개 정답")

        if q["wrong"] and st.button("❌ 오답만 다시 풀기"):
            q["list"] = q["wrong"]
            q["wrong"] = []
            q["idx"] = 0
            q["correct"] = 0
            st.rerun()

        if st.button("⬅ 돌아가기"):
            st.session_state.page = "vocab"
            st.rerun()
        return

    item = lst[q["idx"]]

    q["dir"] = "KO_EN" if st.checkbox("한 → 영") else "EN_KO"

    st.subheader(item["word"] if q["dir"] == "EN_KO" else item["mean"])
    st.write(f"{q['idx'] + 1} / {len(lst)}")

    with st.form("answer"):
        user = st.text_input("정답", autofocus=True)
        submitted = st.form_submit_button("확인")

    if submitted:
        answers = (
            item["mean"].split("/") if q["dir"] == "EN_KO" else [item["word"]]
        )

        if user.strip() in [a.strip() for a in answers]:
            st.success("✅ 정답")
            q["correct"] += 1
        else:
            st.error("❌ 오답")
            item["wrong"] += 1
            q["wrong"].append(item)

        save_db(voca_db)
        q["idx"] += 1
        st.rerun()

# ================= 라우팅 =================
if st.session_state.page == "home":
    home()
elif st.session_state.page == "vocab":
    vocab_page()
elif st.session_state.page == "quiz":
    quiz_page()
