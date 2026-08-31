import os
from datetime import time
from typing import Any

from google import genai
from google.genai import types

from prompt_template import DAILY_SUMMARY_PROMPT, TASK_ANALYSIS_PROMPT
from xiaohongshu_model import DailyTaskList


# 軽量な文章整理に適した安定版モデルを使用する。
# 将来モデルが廃止された場合は、この定数だけを変更すればよい。
MODEL_NAME = "gemini-3.5-flash-lite"


def get_api_key(input_api_key: str) -> str:
    """画面入力を優先し、未入力の場合は環境変数からAPIキーを取得する。"""
    api_key = input_api_key.strip() if input_api_key else os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Gemini APIキーを入力するか、環境変数GEMINI_API_KEYを設定してください。")
    return api_key


def analyze_tasks(source_text: str, input_api_key: str = "") -> DailyTaskList:
    """自由記述の作業メモを、編集可能なタスク一覧へ変換する。"""
    client = genai.Client(api_key=get_api_key(input_api_key))
    prompt = TASK_ANALYSIS_PROMPT.format(source_text=source_text.strip())

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=DailyTaskList,
        ),
    )

    # SDKがPydanticへ変換済みの場合はそのまま返す。
    # parsedが利用できないSDK差異に備え、JSON文字列からの復元も用意する。
    if response.parsed:
        return response.parsed
    if not response.text:
        raise ValueError("AIからタスク分析結果を取得できませんでした。")
    return DailyTaskList.model_validate_json(response.text)


def format_time(value: time) -> str:
    """Streamlitのtime型を日報用のHH:MM形式へ変換する。"""
    return value.strftime("%H:%M")


def build_task_lines(tasks: list[dict[str, Any]]) -> list[str]:
    """ユーザーが確定した時刻と作業内容から、改変されない時間明細を作成する。"""
    sorted_tasks = sorted(tasks, key=lambda task: task["start"])
    return [
        f"{format_time(task['start'])}～{format_time(task['end'])}　{task['content'].strip()}"
        for task in sorted_tasks
        if task["content"].strip()
    ]


def generate_daily_report(
    tasks: list[dict[str, Any]], source_text: str, input_api_key: str = ""
) -> str:
    """確定済みの時間明細とAI要約を結合し、最終的な日報を生成する。"""
    task_lines = build_task_lines(tasks)
    if not task_lines:
        raise ValueError("作業内容が1件もありません。")

    client = genai.Client(api_key=get_api_key(input_api_key))
    prompt = DAILY_SUMMARY_PROMPT.format(
        source_text=source_text.strip(),
        task_lines="\n".join(task_lines),
    )
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2),
    )

    if not response.text:
        raise ValueError("AIから日報要約を取得できませんでした。")

    summary = response.text.strip()
    return "\n".join(task_lines) + "\n\n【本日のまとめ】\n" + summary

