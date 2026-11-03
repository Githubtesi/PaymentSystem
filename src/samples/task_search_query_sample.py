"""
【アプリケーション層・検索パターンサンプル：タスク一覧取得】
このサンプルでは、読み取り専用の「Query」パターンの実装方法を示します。
書き込み（Command）とは異なり、トランザクション（UoW）を必要とせず、
大量のデータを効率よく取得して DTO として返す流れを解説します。

■ 使用しているアプリケーション基盤:
1. Query: 検索条件の定義
2. IQueryHandler: 検索処理の実行
3. PaginatedResult: ページネーション付きの検索結果
4. IIdentityContext: 「自分のデータだけ」を表示するためのフィルタリング
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

# Seedworkからのインポート
from seedwork.application import (
    Query, IQueryHandler, PaginatedResult, Result,
    DTO, Identity, IIdentityContext
)

# ---------------------------------------------------------
# 1. Read Model DTO (読み取り専用のデータ構造)
# ---------------------------------------------------------

@dataclass(frozen=True)
class TaskReadModel(DTO):
    """
    画面表示に最適化されたデータ。
    ドメインモデル（Entity）を直接返すのではなく、必要な項目だけを抽出します。
    """
    id: str
    title: str
    is_completed: bool
    created_at_iso: str

# ---------------------------------------------------------
# 2. Application Layer - Query (検索条件)
# ---------------------------------------------------------

@dataclass(frozen=True)
class SearchTasksQuery(Query):
    """
    タスク検索のためのパラメータ。
    """
    page: int = 1
    page_size: int = 10
    search_keyword: Optional[str] = None
    only_completed: bool = False

# ---------------------------------------------------------
# 3. Application Layer - Query Handler (実行)
# ---------------------------------------------------------

class SearchTasksQueryHandler(IQueryHandler[SearchTasksQuery, PaginatedResult[TaskReadModel]]):
    """
    タスク検索を実行するハンドラ。
    手順：認証 -> 検索条件構築 -> データ取得 -> DTO変換 -> 結果返却
    """
    def __init__(self, identity_context: IIdentityContext):
        self._identity_context = identity_context
        # 本来はここに読み取り専用のリポジトリやDB接続（ReadOnlyRepo）を注入します

    def handle(self, query: SearchTasksQuery) -> PaginatedResult[TaskReadModel]:
        # A. 誰のデータを検索するかを特定 (Identity)
        identity = self._identity_context.get_current_identity()
        if not identity.is_authenticated:
            # 認証されていない場合は空の結果を返す、または例外
            return PaginatedResult(items=[], total_count=0, page=query.page, page_size=query.page_size)

        print(f"[QueryHandler] ユーザー {identity.username} のタスクを検索中... (キーワード: {query.search_keyword})")

        # B. データ取得のシミュレーション (本来はDBからSQLやリポジトリで取得)
        # ここではモックデータを作成
        all_mock_data = [
            TaskReadModel("t-1", "設計書を作成する", True, "2024-01-01T10:00:00"),
            TaskReadModel("t-2", "レビューを依頼する", False, "2024-01-02T11:00:00"),
            TaskReadModel("t-3", "コードをプッシュする", False, "2024-01-03T12:00:00"),
        ]
        
        # 簡易的なフィルタリング（本来はDB側のWHERE句で行う）
        filtered_items = [
            item for item in all_mock_data 
            if (not query.search_keyword or query.search_keyword in item.title)
        ]

        # C. ページネーション付きの結果を返却 (PaginatedResult)
        return PaginatedResult(
            items=filtered_items,
            total_count=len(filtered_items),
            page=query.page,
            page_size=query.page_size
        )

# ---------------------------------------------------------
# 4. Infrastructure Layer - Mocks
# ---------------------------------------------------------

class MockIdentityContext(IIdentityContext):
    def __init__(self, username: str):
        self._user = Identity(user_id="u-001", username=username, is_authenticated=True)
    def get_current_identity(self) -> Identity:
        return self._user

# ---------------------------------------------------------
# 5. Execution (メイン処理)
# ---------------------------------------------------------

if __name__ == "__main__":
    # A. 準備
    ctx = MockIdentityContext(username="suzuki_taro")
    handler = SearchTasksQueryHandler(ctx)

    # B. クエリの作成 (1ページ目、キーワード指定)
    query = SearchTasksQuery(page=1, page_size=5, search_keyword="作成")

    # C. 検索実行
    result = handler.handle(query)

    # D. 結果の表示
    print(f"\n--- 検索結果 (合計: {result.total_count}件) ---")
    print(f"ページ: {result.page} / 総ページ数: {result.total_pages}")
    
    for task in result.items:
        status = "✅" if task.is_completed else "⭕"
        print(f"{status} [{task.id}] {task.title} (作成日: {task.created_at_iso})")
