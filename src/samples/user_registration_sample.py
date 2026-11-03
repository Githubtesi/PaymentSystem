"""
【解説：このサンプルの仕組み】
このプログラムは、新しいユーザーがシステムに「正しく」登録されるまでの流れを表現しています。

1. [値のチェック]：IDやメールアドレスが変なデータじゃないか確認します（ValueObject）
2. [ユーザーを作る]：チェックを通ったデータで「ユーザー」という実体を作ります（Entity/AggregateRoot）
3. [出来事を記録]：「登録された！」という事実をメモします（DomainEvent）
4. [保存する]：ユーザーのデータを箱（DB）にしまいます（Repository）
5. [お知らせする]：登録されたメモを見て、お祝いメールを送ります（EventPublisher/Subscriber）

このように役割を分けることで、後から「メールじゃなくてLINEを送りたい」といった変更が楽になります。
"""

from dataclasses import dataclass
from seedwork.domain import (
    ValueObject, 
    AggregateRoot, 
    IRepository, 
    DomainEvent, 
    DomainEventSubscriber, 
    publisher,
    ValueObjectValidationError
)

# ---------------------------------------------------------
# 1. 値のルールを決める（Value Objects）
# ---------------------------------------------------------

@dataclass(frozen=True)
class UserId(ValueObject):
    """ユーザーのID。空っぽのIDは許しません。"""
    value: str

    def validate(self):
        if not self.value:
            # データが正しくない場合は、専用のエラーを投げてストップさせます
            raise ValueObjectValidationError("IDを入力してください", "UserId")

@dataclass(frozen=True)
class Email(ValueObject):
    """メールアドレス。必ず '@' が入っているかチェックします。"""
    value: str

    def validate(self):
        if "@" not in self.value:
            raise ValueObjectValidationError("メールアドレスの形式が正しくありません", "Email")

# ---------------------------------------------------------
# 2. 起こった出来事を定義する（Domain Event）
# ---------------------------------------------------------

@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    """
    「ユーザーが登録された」という過去の事実を表します。
    この中には、後でお知らせ（通知）に使うデータを入れておきます。
    """
    user_name: str
    email: str

# ---------------------------------------------------------
# 3. ユーザーという「物」を定義する（Aggregate Root）
# ---------------------------------------------------------

@dataclass
class User(AggregateRoot[UserId]):
    """
    ユーザー本人を表します。ID、名前、メールを保持します。
    AggregateRoot を継承することで、「出来事(Event)」を記録できるようになります。
    """
    name: str
    email: Email

    @classmethod
    def create(cls, user_id: UserId, name: str, email: Email) -> "User":
        """
        新しいユーザーを作るための専用メソッドです。
        「作る」と同時に「登録イベント」を内部にメモします。
        """
        # インスタンス（実体）の作成
        user = cls(id=user_id, name=name, email=email)
        
        # 「登録されました」というイベントを自分の中に記録する
        user.record_event(UserRegistered(
            aggregate_id=user_id.value,
            user_name=name,
            email=email.value
        ))
        return user

# ---------------------------------------------------------
# 4. 保存の窓口を作る（Repository Interface）
# ---------------------------------------------------------

class IUserRepository(IRepository[User]):
    """
    「ユーザーを保存したり探したりする機能」のルールです。
    実際の方法（SQLを使うのか、メモリに置くのか）はこの段階では気にしません。
    """
    pass

# ---------------------------------------------------------
# 5. 実際に保存する仕組み（Infrastructure Implementation）
# ---------------------------------------------------------

class InMemoryUserRepositoryImpl(IUserRepository):
    """
    テスト用に、メモリ（プログラム内の変数）に保存する仕組みです。
    """
    def __init__(self):
        self._items = {}

    def next_identity(self) -> str:
        """新しいユニークなID（UUID）を発行します"""
        import uuid
        return str(uuid.uuid4())

    def save(self, user: User) -> None:
        """データを保存します"""
        self._items[user.id.value] = user
        print(f"[システム] {user.name} さんのデータを保存しました。")

    def find_by_id(self, user_id: str):
        return self._items.get(user_id)

    def delete(self, user_id: str):
        if user_id in self._items: del self._items[user_id]

    def find_all(self):
        return list(self._items.values())

# ---------------------------------------------------------
# 6. イベントに反応する人（Subscriber / Notification）
# ---------------------------------------------------------

class NotificationHandler(DomainEventSubscriber):
    """
    登録イベントが発生したら「通知」を担当するクラスです。
    """
    @property
    def subscribed_to_type(self):
        # どのイベントに反応するかを指定します
        return UserRegistered

    def handle(self, event: UserRegistered):
        # 実際に通知する処理を書きます
        print(f"[通知サービス] {event.user_name} 様宛に確認メール({event.email})を送信しました。")

# ---------------------------------------------------------
# 7. 登録の流れをまとめる（Application Service）
# ---------------------------------------------------------

class RegisterUserAppService:
    """
    ユーザー登録の「手順」を管理するマネージャーです。
    """
    def __init__(self, repository: IUserRepository):
        self._repository = repository

    def run(self, input_name: str, input_email: str):
        print(f"\n--- ユーザー登録の受付を開始します: {input_name} ---")
        
        try:
            # 1. IDを新しく発行する
            new_id_str = self._repository.next_identity()
            user_id = UserId(new_id_str) # ここでIDが空でないかチェックが入る
            
            # 2. メールアドレスを型に変換する
            email = Email(input_email) # ここで「@」が入っているかチェックが入る
            
            # 3. ユーザーを作成する（イベントも内部で記録される）
            user = User.create(user_id=user_id, name=input_name, email=email)
            
            # 4. リポジトリを使って保存する
            self._repository.save(user)
            
            # 5. 記録しておいたイベント（登録通知）を発行する
            # これにより、NotificationHandler が動き出します
            events = user.pull_events()
            publisher.publish_all(events)
            
            print(f"--- 登録がすべて完了しました (ID: {user_id.value}) ---\n")

        except ValueObjectValidationError as e:
            # バリデーションエラーが起きた場合の処理
            print(f"【入力エラー】{e.message}")
        except Exception as e:
            print(f"【エラー】予期せぬ問題が発生しました: {e}")

# ---------------------------------------------------------
# 8. プログラムを動かす（Main）
# ---------------------------------------------------------

if __name__ == "__main__":
    # A. 最初に「通知担当者」を登録しておく
    publisher.subscribe(NotificationHandler())

    # B. 保存の仕組みを用意する
    repo = InMemoryUserRepositoryImpl()

    # C. マネージャーを用意する
    app_service = RegisterUserAppService(repo)

    # --- ケース1: 正しく入力した場合 ---
    app_service.run("山田 太郎", "yamada@example.com")

    # --- ケース2: メールアドレスが間違っている場合 ---
    app_service.run("エラー ユーザー", "not-an-email")
