import streamlit as st
from openai import OpenAI
import json, os

# ================= 설정 =================
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

# ================= 상태 =================
if "page" not in st.session_state:
    st.session_state.page = "home"

if "current_session" not in st.session_state:
    st.session_state.current_session = None

if "quiz" not in st.session_state:
    st.session_state.quiz = {}

voca_db = load_db()

# ================= 홈 =================
def home():
    st.title("📚 단어장 선택")

    with st.form("create_session", clear_on_submit=True):
        name = st.text_input("회차")
        submitted = st.form_submit_button("생성")
        if submitted and name:
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
    session = st.session_state.current_session
    st.title(session)

    if st.button("⬅ 회차 선택"):
        st.session_state.page = "home"
        st.rerun()

    # -------- 단어 추가 --------
    with st.form("add_word", clear_on_submit=True):
        word = st.text_input("영어 단어")
        mean = st.text_input("뜻 (/로 구분)")
        submitted = st.form_submit_button("추가")

        if submitted and word:
            ai_mean = client.responses.create(
                model="gpt-4.1-mini",
                input=f"영어 단어 '{word}'의 가장 많이 쓰이는 한국어 뜻을 핵심 단어만 / 로 구분해서 알려줘."
            ).output_text.strip()

            user_set = set(mean.split("/")) if mean else set()
            ai_set = set(ai_mean.split("/"))
            final_mean = "/".join(user_set.union(ai_set))

            voca_db[session].append({
                "word": word,
                "mean": final_mean,
                "wrong": 0
            })
            save_db(voca_db)
            st.rerun()

    st.divider()
    st.subheader("📋 단어 목록")

    for i, item in enumerate(voca_db[session]):
        col1, col2 = st.columns([5, 1])

        with col1:
            st.markdown(f"**{item['word']}**")
            new_mean = st.text_input(
                "",
                value=item["mean"],
                key=f"mean_{i}"
            )
            if new_mean != item["mean"]:
                item["mean"] = new_mean
                save_db(voca_db)

        with col2:
            if st.button("🗑", key=f"del_{i}"):
                voca_db[session].remove(item)
                save_db(voca_db)
                st.rerun()

    st.divider()
    if st.button("▶ 퀴즈 시작"):
        quiz_list = sorted(voca_db[session], key=lambda x: -x["wrong"])
        st.session_state.quiz = {
            "list": quiz_list,
            "wrong": [],
            "idx": 0,
            "correct": 0,
            "state": "CHECK",
            "dir": "EN_KO"
        }
        st.session_state.page = "quiz"
        st.rerun()

# ================= 퀴즈 =================
def quiz_page():
    qz = st.session_state.quiz
    lst = qz["list"]

    if qz["idx"] >= len(lst):
        st.title("🏁 퀴즈 종료")
        st.write(f"{len(lst)}문제 중 {qz['correct']}개 정답")

        if st.button("❌ 오답만 다시 풀기"):
            qz["list"] = qz["wrong"]
            qz["wrong"] = []
            qz["idx"] = 0
            qz["correct"] = 0
            st.rerun()

        if st.button("⬅ 돌아가기"):
            st.session_state.page = "vocab"
            st.rerun()
        return

    q = lst[qz["idx"]]

    if st.checkbox("한 → 영"):
        qz["dir"] = "KO_EN"
    else:
        qz["dir"] = "EN_KO"

    st.write(f"{qz['idx'] + 1} / {len(lst)}")
    st.subheader(q["word"] if qz["dir"] == "EN_KO" else q["mean"])

    with st.form("answer"):
        ans = st.text_input("정답")
        submitted = st.form_submit_button("확인")

        if submitted:
            if qz["state"] == "CHECK":
                answers = (
                    [a.strip() for a in q["mean"].split("/")]
                    if qz["dir"] == "EN_KO"
                    else [q["word"]]
                )

                if ans.strip() in answers:
                    st.success("정답")
                    qz["correct"] += 1
                else:
                    st.error("오답")
                    q["wrong"] += 1
                    qz["wrong"].append(q)

                qz["state"] = "NEXT"
            else:
                qz["idx"] += 1
                qz["state"] = "CHECK"

            st.rerun()

# ================= 실행 =================
if st.session_state.page == "home":
    home()
elif st.session_state.page == "vocab":
    vocab_page()
else:
    quiz_page()
