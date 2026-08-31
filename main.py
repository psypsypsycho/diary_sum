from datetime import time, timedelta, datetime

import streamlit as st

from utils import analyze_tasks, generate_daily_report


# ページ全体の基本設定。wideを指定し、時刻欄と作業内容欄を横に並べやすくする。
st.set_page_config(page_title="AI日報作成ツール", page_icon="📝", layout="wide")


def initialize_session_state() -> None:
    """Streamlitの再実行後も保持したいデータを初期化する。"""
    if "tasks" not in st.session_state:
        st.session_state.tasks = []
    if "report" not in st.session_state:
        st.session_state.report = ""
    if "source_text" not in st.session_state:
        st.session_state.source_text = ""


def default_time(index: int) -> tuple[time, time]:
    """AI抽出直後に表示する仮の開始・終了時刻を30分単位で作成する。"""
    start = datetime.combine(datetime.today(), time(9, 0)) + timedelta(minutes=30 * index)
    end = start + timedelta(minutes=30)
    return start.time(), end.time()


def sync_widget_values() -> None:
    """前回の画面操作で変更されたウィジェット値をタスク本体へ反映する。"""
    for task in st.session_state.tasks:
        task_id = task["id"]
        start_key = f"start_{task_id}"
        end_key = f"end_{task_id}"
        content_key = f"content_{task_id}"

        if start_key in st.session_state:
            task["start"] = st.session_state[start_key]
        if end_key in st.session_state:
            task["end"] = st.session_state[end_key]
        if content_key in st.session_state:
            task["content"] = st.session_state[content_key]


initialize_session_state()
sync_widget_values()

st.title("AI日報作成ツール 📝")
st.caption("作業メモをタスクに分解し、時刻を調整してから提出用の日報を作成します。")

# APIキーはStreamlit CloudのSecretsから自動取得する。
# ブラウザにはAPIキーを表示・送信しない。
api_key = ""

with st.sidebar:
    st.success("AI機能を利用できます")
    st.info("社外秘・個人情報・顧客情報は入力しないでください。")

st.subheader("1. 今日行ったことを入力")
source_text = st.text_area(
    "箇条書きでも文章でも入力できます",
    value=st.session_state.source_text,
    height=150,
    placeholder="例：午前は生産管理コースを学習し、午後は課題⑤の設計書を修正した。最後にPC内の資料を整理した。",
)

if st.button("① タスクを分析", type="primary", use_container_width=True):
    if not source_text.strip():
        st.warning("今日行ったことを入力してください。")
    else:
        try:
            with st.spinner("入力内容からタスクを抽出しています..."):
                analyzed = analyze_tasks(source_text, api_key)

            tasks = []
            for index, item in enumerate(analyzed.tasks):
                start, end = default_time(index)
                tasks.append(
                    {
                        "id": index,
                        "content": item.content,
                        "start": start,
                        "end": end,
                    }
                )

            st.session_state.tasks = tasks
            st.session_state.source_text = source_text
            st.session_state.report = ""

            # 新しいタスクに対応する古いウィジェット値が残らないように削除する。
            for key in list(st.session_state.keys()):
                if key.startswith(("start_", "end_", "content_")):
                    del st.session_state[key]
            st.rerun()
        except Exception as error:
            st.error(f"タスク分析に失敗しました：{error}")


if st.session_state.tasks:
    st.divider()
    st.subheader("2. タスクの時刻と内容を調整")
    st.caption("時刻を変更すると、開始時刻が早い順に自動で並び替えられます。")

    # 画面表示前に開始時刻で並べる。時刻変更時はStreamlitが自動再実行するため、
    # 次の描画では新しい順番が即座に反映される。
    sorted_tasks = sorted(st.session_state.tasks, key=lambda task: task["start"])
    has_invalid_time = False

    for task in sorted_tasks:
        task_id = task["id"]
        time_column, content_column = st.columns([1.2, 4])

        with time_column:
            start_col, end_col = st.columns(2)
            with start_col:
                task["start"] = st.time_input(
                    "開始",
                    value=task["start"],
                    step=300,
                    key=f"start_{task_id}",
                )
            with end_col:
                task["end"] = st.time_input(
                    "終了",
                    value=task["end"],
                    step=300,
                    key=f"end_{task_id}",
                )

        with content_column:
            task["content"] = st.text_input(
                "作業内容",
                value=task["content"],
                key=f"content_{task_id}",
            )

        if task["end"] <= task["start"]:
            has_invalid_time = True
            st.warning(f"「{task['content']}」の終了時刻を開始時刻より後にしてください。")

    st.session_state.tasks = sorted_tasks

    if st.button(
        "② 日報を生成",
        type="primary",
        use_container_width=True,
        disabled=has_invalid_time,
    ):
        try:
            with st.spinner("提出用の日報を作成しています..."):
                st.session_state.report = generate_daily_report(
                    st.session_state.tasks,
                    st.session_state.source_text,
                    api_key,
                )
        except Exception as error:
            st.error(f"日報生成に失敗しました：{error}")


if st.session_state.report:
    st.divider()
    st.subheader("3. 生成された日報")
    st.text_area("必要に応じて修正してからコピーしてください", st.session_state.report, height=320)
    # st.code右上のコピーボタンを利用できるよう、同じ内容を純テキストとして表示する。
    st.code(st.session_state.report, language=None)

