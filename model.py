from typing import List

from pydantic import BaseModel, Field


class DailyTask(BaseModel):
    """AIが入力文から抽出する1件分の作業タスク。"""

    content: str = Field(
        description="日報の時間明細にそのまま使用できる、簡潔で事実に忠実な日本語の作業内容"
    )


class DailyTaskList(BaseModel):
    """1回目のAI実行結果を受け取るための構造化データ。"""

    tasks: List[DailyTask] = Field(
        description="入力文に含まれる作業を、重複なく実施単位に分けた一覧",
        min_length=1,
        max_length=12,
    )

