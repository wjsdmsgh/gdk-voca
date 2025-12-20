import flet as ft
from openai import OpenAI
import json, os, random

OPENAI_API_KEY = ""
client = OpenAI(api_key=OPENAI_API_KEY)

DATA_FILE = "voca.json"


def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_db(db):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def main(page: ft.Page):
    page.title = "AI 영어 단어장"
    page.window_width = 520
    page.window_height = 900

    voca_db = load_db()
    current_session = None

    quiz_list = []
    wrong_list = []
    idx = 0
    correct = 0
    state = "CHECK"
    quiz_dir = "EN_KO"

    # ================= 홈 =================
    def home():
        page.clean()

        session_col = ft.Column()

        def refresh():
            session_col.controls.clear()
            for s in voca_db:
                session_col.controls.append(
                    ft.ElevatedButton(
                        s, on_click=lambda e, ss=s: open_vocab(ss)
                    )
                )
            page.update()

        session_in = ft.TextField(
            label="회차 (예: 24년 3월)",
            on_submit=lambda e: create()
        )

        def create():
            name = session_in.value.strip()
            if not name:
                return
            voca_db.setdefault(name, [])
            save_db(voca_db)
            open_vocab(name)

        page.add(
            ft.Text("📚 단어장 선택", size=26, weight="bold"),
            session_in,
            ft.ElevatedButton("➕ 새로 만들기", on_click=lambda e: create()),
            ft.Divider(),
            session_col
        )
        refresh()

    def open_vocab(name):
        nonlocal current_session
        current_session = name
        vocab_page()

    # ================= 단어장 =================
    def vocab_page():
        page.clean()

        word_in = ft.TextField(label="영어 단어", autofocus=True)
        mean_in = ft.TextField(label="뜻 (/로 구분)")

        word_list = ft.Column(scroll="auto", height=260)

        def add_word():
            w = word_in.value.strip()
            user_mean = mean_in.value.strip()

            if not w:
                return

            ai_mean = client.responses.create(
                model="gpt-4.1-mini",
                input=f"영어 단어 '{w}'의 가장 많이 쓰이는 한국어 뜻을 핵심 단어만 / 로 구분해서 알려줘."
            ).output_text.strip()

            user_set = set(user_mean.split("/")) if user_mean else set()
            ai_set = set(ai_mean.split("/"))
            final_mean = "/".join(user_set.union(ai_set))

            voca_db[current_session].append({
                "word": w,
                "mean": final_mean,
                "wrong": 0
            })
            save_db(voca_db)

            word_in.value = ""
            mean_in.value = ""
            word_in.focus()
            refresh_list()

        word_in.on_submit = lambda e: mean_in.focus()
        mean_in.on_submit = lambda e: add_word()

        def refresh_list():
            word_list.controls.clear()
            for item in voca_db[current_session]:
                tf = ft.TextField(
                    value=item["mean"],
                    on_change=lambda e, it=item: it.update({"mean": e.control.value})
                )

                word_list.controls.append(
                    ft.Row([
                        ft.Column([
                            ft.Text(item["word"], weight="bold"),
                            tf
                        ], expand=True),
                        ft.IconButton(
                            ft.Icons.DELETE,
                            icon_color="red",
                            on_click=lambda e, it=item: delete(it)
                        )
                    ])
                )
            page.update()

        def delete(it):
            voca_db[current_session].remove(it)
            save_db(voca_db)
            refresh_list()

        page.add(
            ft.ElevatedButton("⬅ 회차 선택", on_click=lambda e: home()),
            ft.Text(current_session, size=24, weight="bold"),
            word_in,
            mean_in,
            ft.Divider(),
            ft.Text("📋 단어 목록"),
            word_list,
            ft.Divider(),
            ft.ElevatedButton("▶ 퀴즈 시작", on_click=lambda e: quiz_page())
        )
        refresh_list()

    # ================= 퀴즈 =================
        # ================= 퀴즈 =================
    def quiz_page():
        nonlocal quiz_list, wrong_list, idx, correct, state, quiz_dir

        page.clean()
        quiz_list = sorted(
            voca_db[current_session],
            key=lambda x: -x["wrong"]
        )
        wrong_list = []
        idx = 0
        correct = 0
        state = "CHECK"

        q_text = ft.Text("", size=24, weight="bold")
        prog = ft.Text("")
        ans = ft.TextField(autofocus=True)
        res = ft.Text("", size=18)

        toggle = ft.Switch(
            label="영 → 한",
            value=False,
            on_change=lambda e: set_dir(e.control.value)
        )

        def set_dir(v):
            nonlocal quiz_dir
            quiz_dir = "KO_EN" if v else "EN_KO"
            toggle.label = "한 → 영" if v else "영 → 한"
            show()

        def show():
            nonlocal state
            if idx >= len(quiz_list):
                end()
                return

            q = quiz_list[idx]
            q_text.value = q["word"] if quiz_dir == "EN_KO" else q["mean"]
            prog.value = f"{idx + 1} / {len(quiz_list)}"
            ans.value = ""
            res.value = ""
            state = "CHECK"
            ans.focus()
            page.update()

        def submit(e):
            nonlocal idx, correct, state

            q = quiz_list[idx]

            # 1️⃣ 정답 체크 단계
            if state == "CHECK":
                user = ans.value.strip()

                if quiz_dir == "EN_KO":
                    answers = [a.strip() for a in q["mean"].split("/")]
                else:
                    answers = [q["word"]]

                if user in answers:
                    res.value = "✅ 정답"
                    correct += 1
                else:
                    res.value = "❌ 오답"
                    q["wrong"] += 1
                    wrong_list.append(q)

                state = "NEXT"
                ans.focus()  # ⭐ 핵심: 포커스 유지

            # 2️⃣ 다음 문제로 이동
            else:
                idx += 1
                show()

            page.update()

        ans.on_submit = submit

        def end():
            page.clean()
            page.add(
                ft.Text("🏁 퀴즈 종료", size=26, weight="bold"),
                ft.Text(f"{len(quiz_list)}문제 중 {correct}개 정답"),
                ft.ElevatedButton("❌ 오답만 다시 풀기", on_click=lambda e: retry()),
                ft.ElevatedButton("⬅ 돌아가기", on_click=lambda e: vocab_page())
            )

        def retry():
            nonlocal quiz_list, idx, correct
            quiz_list = wrong_list
            idx = 0
            correct = 0
            show()

        page.add(toggle, prog, q_text, ans, res)
        show()