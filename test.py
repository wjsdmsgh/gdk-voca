import streamlit as st
import json, os
from openai import OpenAI

# ================= 기본 설정 =================
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
        "state": "CHECK",
        "dir": "EN_KO"
    }

# ================= 홈 =================
def home():
    st.title("📚 단어장 선택")

    name = st.text_input("회차 (예: 24년 3월)")

    if st.button("➕ 새로 만들기") and name:
        voca_db.setdefault(name, [])
        save_db(voca_db)
        st.session_state.current_session = name
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

    word = st.text_input("영어 단어")
    mean = st.text_input("뜻 (/로 구분)")

    if st.button("단어 추가") and word:
        ai_mean = client.responses.create(
            model="gpt-4.1-mini",
            input=f"영어 단어 '{word}'의 가장 많이 쓰이는 한국어 뜻을 핵심 단어만 / 로 구분해서 알려줘."
        ).output_text.strip()

        user_set = set(mean.split("/")) if mean else set()
        ai_set = set(ai_mean.split("/"))
        final = "/".join(user_set | ai_set)

        voca_db[s].append({
            "word": word,
            "mean": final,
            "wrong": 0
        })
        save_db(voca_db)
        st.rerun()

    st.divider()
    st.subheader("📋 단어 목록")

    for i, v in enumerate(voca_db[s]):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"**{v['word']}** — {v['mean']}")
        with col2:
            if st.button("❌", key=f"del{i}"):
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
        q["state"] = "CHECK"
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

        if q["wrong"]:
            if st.button("❌ 오답만 다시 풀기"):
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

    if st.checkbox("한 → 영"):
        q["dir"] = "KO_EN"
    else:
        q["dir"] = "EN_KO"

    st.write(f"### {item['word'] if q['dir']=='EN_KO' else item['mean']}")
    st.write(f"{q['idx'] + 1} / {len(lst)}")

    with st.form("answer"):
        user = st.text_input("정답 입력", autofocus=True)
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
