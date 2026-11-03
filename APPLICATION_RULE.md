# アプリケーション層選定・実装ガイドライン

## 1. 役割

アプリケーション層は、**ユースケースを実行するための処理手順を調整する層**です。

Domainが「何が正しいか」「どの状態が許されるか」を表現するのに対し、Applicationは「そのDomainのルールを使って、何をどの順番で実行するか」を表現します。

基本的な責務は次のとおりです。

- **Domain**: 業務ルール、不変条件、業務上の判断
- **Application**: ユースケース、処理順序、入出力、必要なトランザクション境界の調整
- **Infrastructure**: DB、ORM、外部API、ファイル、メッセージング等の技術的実装

### 重要な方針

Application層では、**必要以上に部品や抽象を増やさない**ことを基本とします。

Command、Query、DTO、Result、Repository、Unit of Work、Bus、Identity Context等は、DDDやClean Architectureでよく使われる手段ですが、**すべてのユースケースで必須ではありません**。

> **具体的に実装できるものは具体的に実装し、必要になった時点で抽象化・分割する。**

この方針は ARCHITECTURE_RULE.md の「具体化を優先し、必要になったら抽象化する」に従います。

---

## 2. Application層で守るべき境界

実装方法は柔軟に選択できますが、以下の境界は守ります。

### 必ず守ること

- 業務ルールはDomainに置く。
- Applicationはユースケースの調整を担当する。
- Infrastructureの技術詳細をApplicationの業務ロジックへ持ち込まない。
- Domainの責務をApplicationへ重複実装しない。
- 外部入力をそのまま信用せず、必要な検証を行う。
- トランザクションが必要な場合は、その境界を明確にする。
- ApplicationからInfrastructureの具体実装へ直接依存する場合は、その理由を明確にする。

### 原則として避けること

- Application Serviceを巨大化させる。
- 小さな処理のためにCommand / Query / Handler / DTO / Result等を大量に作る。
- 将来の可能性だけを理由にInterfaceを作る。
- 「DDDだから」「Clean Architectureだから」という理由だけでRepositoryやUnit of Workを追加する。
- Domainの業務判断をApplicationにコピーする。

---

## 3. 実装方式の選択

Application層には、複数の実装方式があります。

### 小さなユースケース

単純な処理であれば、1つの関数や小さなクラスで十分です。

~~~python
def register_member(member_id: str, name: str) -> None:
    member = Member.register(member_id, name)
    member_repository.save(member)
~~~

この程度の処理に、必ずCommand、Handler、DTO、Bus等を追加する必要はありません。

### 少し複雑なユースケース

処理の手順や依存関係が増えてきたら、Use CaseクラスやApplication Serviceへ分離します。

~~~python
class RegisterMember:
    def __init__(self, repository):
        self.repository = repository

    def execute(self, member_id: str, name: str) -> None:
        member = Member.register(member_id, name)
        self.repository.save(member)
~~~

### 複雑になった場合

必要に応じて、以下を段階的に導入します。

- Command
- Query
- Query Handler
- DTO
- Result
- Repository abstraction
- Unit of Work
- Identity Context
- Command / Query Bus
- Domain Event Publisher

**最初から全部導入する必要はありません。**

---

## 4. 部品の選定基準

| 部品 | 採用 | 主な理由 |
| :--- | :--- | :--- |
| **Use Case** | 必要に応じて | ユースケースの責務を明確にしたい |
| **Application Service** | 必要に応じて | 複数のDomain処理を調整したい |
| **Command** | 必要に応じて | 入力の意図を明確にしたい |
| **Query** | 必要に応じて | 読み取り処理を明確に分離したい |
| **Query Handler** | 必要に応じて | Query処理が複雑・増加した |
| **DTO** | 必要に応じて | 層や境界をまたぐデータ形式を固定したい |
| **Result** | 必要に応じて | 成功・失敗を値として扱いたい |
| **Application Exception** | 必要に応じて | Application固有のエラーを整理したい |
| **Identity Context** | 必要に応じて | 実行主体をApplicationから取得したい |
| **Command / Query Bus** | 必要に応じて | メッセージ配送自体が複雑になった |
| **Unit of Work** | 必要に応じて | 複数操作のトランザクション境界を明示したい |
| **Repository abstraction** | 必要に応じて | Domain/Applicationと永続化技術を分離する必要がある |

### 判断の原則

「存在するべきか」ではなく、

> **この部品を導入することで、現在のコードの複雑さが減るか、責務が明確になるか、境界を守れるか**

で判断します。

---

## 5. Use Case / Application Service

Use CaseやApplication Serviceは、**処理を調整するオーケストレーター**です。

典型的には次のような流れになります。

~~~text
入力
 ↓
Application
 ↓
必要なデータを取得
 ↓
Domainの処理を呼び出す
 ↓
必要なら保存
 ↓
必要ならトランザクションを確定
 ↓
出力
~~~

ただし、これは固定された実装テンプレートではありません。

### 禁止事項

- Application Serviceへ業務ルールを書かない。
- Entityの属性を直接変更して業務ルールを回避しない。
- Domain Exceptionと同じ意味の判定をApplicationへ重複実装しない。
- ApplicationからSQLを直接実行する場合は、技術的境界を意識せず無秩序に実装しない。
- Infrastructureの具体実装へ依存する場合、その依存を「なんとなく」で増やさない。

### 許容されること

小規模な機能では、Applicationから具体的なRepositoryやInfrastructure部品を利用する実装も、**プロジェクトの規模・境界・テスト要件に照らして妥当なら許容**します。

ただし、具体実装への依存が原因で責務分離が崩れたり、交換・テスト・再利用が難しくなった場合は、抽象化を検討します。

---

## 6. Command / Query

CommandとQueryは、必要な場合に利用します。

### Command

状態変更の意図を表現するための入力モデルです。

~~~python
@dataclass(frozen=True)
class RegisterMemberCommand:
    member_id: str
    name: str
~~~

Command自体に業務ロジックを持たせる必要はありません。

### Query

状態を変更せず情報を取得する意図を表現します。

~~~python
@dataclass(frozen=True)
class FindMemberQuery:
    member_id: str
~~~

### 注意

「状態変更だから必ずCommand」「読み取りだから必ずQuery」とする必要はありません。

単純な処理では、通常の関数引数で十分な場合があります。

---

## 7. DTO / Result

DTOやResultは、**境界を明確にする必要がある場合に利用**します。

### DTOを検討するケース

- PresentationとApplicationのデータ形式を分離したい。
- 外部APIとの契約を固定したい。
- Domain Entityを外部へ公開したくない。
- 入出力モデルが複雑になった。

単純なユースケースでは、DTOを作らずプリミティブ値や小さなデータ構造を利用しても構いません。

### Resultを検討するケース

- 成功・失敗を値として明示的に扱いたい。
- 例外を使わず結果を返す設計が適している。
- 呼び出し側で複数の結果パターンを扱う必要がある。

Resultも全ユースケースの必須部品ではありません。

---

## 8. Repository

Repository abstractionは**必要になった場合に導入**します。

### Repositoryを検討する理由

- Domainと永続化技術を明確に分離したい。
- 実装を差し替える必要がある。
- テストで永続化処理を置き換える必要がある。
- Aggregateの取得・保存というDomain上の境界を表現したい。
- Infrastructureへの依存がApplicationへ広がっている。

### Repositoryを作らない選択

単純な小規模機能で、ConcreteなRepositoryを直接利用する方が理解しやすい場合は、無理にInterfaceを追加しません。

### 禁止される導入理由

以下だけを理由にRepository abstractionを追加しないでください。

- 「DDDだから」
- 「Clean Architectureだから」
- 「将来DBを変更するかもしれないから」
- 「Interfaceがあった方が綺麗だから」
- 「AIが生成しやすいから」

---

## 9. Unit of Work

Unit of Workは、**複数の操作を1つのトランザクション境界として扱う必要がある場合に利用**します。

~~~python
with unit_of_work:
    ...
~~~

単一操作でトランザクション境界が明確な場合など、別の仕組みで十分ならUnit of Workを追加する必要はありません。

導入する場合は、Applicationが「どこからどこまでを1つの処理として扱うか」を表現し、具体的なDBトランザクション処理はInfrastructure側で担当します。

---

## 10. Identity

認証済みユーザーや実行主体がユースケースに必要な場合、Identityを利用します。

必要に応じて IIdentityContext のような抽象を導入できます。

~~~text
Presentation / Infrastructure
        ↓
Identity Context
        ↓
Application
~~~

ただし、小さなアプリケーションで実行主体の取得が単純であり、具体実装への依存が問題にならない場合は、過剰な抽象化を避けても構いません。

---

## 11. Domain Event

Domain Eventが必要な場合、Applicationはイベントの配送や後続処理を調整します。

Application層でDomain Eventの業務的意味を再実装しないでください。

ただし、単純なユースケースにイベント機構を無理に導入する必要はありません。

---

## 12. 例外

Application固有の例外が必要な場合は、Application Exceptionを定義します。

| 種類 | 主な意味 |
| :--- | :--- |
| AppException | Application層の共通例外 |
| ValidationError | 入力・要求内容の不備 |
| AuthorizationError | Application上の権限不足 |
| ResourceNotFoundError | 必要なリソースが存在しない |

ただし、既存の例外体系で十分なら、例外を増やす必要はありません。

### 責務の分離

- **Domain Exception**: 業務ルール違反
- **Application Exception**: ユースケース上のエラー
- **Infrastructure Exception**: DB・外部サービス等の技術エラー

同じ意味のエラーを複数層で重複定義しないことを優先します。

---

## 13. VSAとの関係

本プロジェクトでは、Application層の構造は**Vertical Slice Architecture（VSA）を優先**します。

機能ごとに、その機能を実現するコードを近くに配置します。

~~~text
src/
├── seedwork/
├── shared_kernel/
└── features/
    └── member_management/
        ├── register_member.py
        ├── find_member.py
        └── ...
~~~

これは一例であり、固定構造ではありません。

機能が大きくなった場合は、必要に応じて分割します。

~~~text
member_management/
├── register_member/
│   ├── use_case.py
│   ├── dto.py
│   └── ...
└── find_member/
    ├── use_case.py
    └── ...
~~~

さらに複雑になった場合のみ、Command、Handler、Repository、Infrastructure等へ分離します。

> **最初から階層を作るのではなく、複雑さに応じて構造を成長させる。**

詳細なモジュール境界は MODULE_RULE.md および ARCHITECTURE_RULE.md に従います。

---

## 14. Application層の設計原則

Application層では、次の優先順位で判断します。

1. **Domainの責務を守る**
2. **ApplicationとInfrastructureの境界を守る**
3. **ユースケースの処理手順を理解しやすくする**
4. **必要最小限の部品で実装する**
5. **複雑になったら分割・抽象化する**

### 具体化 → 分割 → 抽象化

原則として次の順番で進めます。

~~~text
単純な具体実装
      ↓
複雑になってきた
      ↓
責務を分割
      ↓
同じ問題が繰り返される
      ↓
必要な部分だけ抽象化
~~~

「抽象化 → 実装」から始めることを基本としません。

---

## 15. 実装チェックリスト

### 必須確認

- [ ] これはユースケースの手順であり、業務ルールではないか
- [ ] 業務ルールをDomainへ委譲できているか
- [ ] ApplicationとInfrastructureの責務が混ざっていないか
- [ ] ユースケースの流れをコードから理解できるか
- [ ] 不要な複雑さを追加していないか

### 必要に応じて確認

- [ ] Commandが必要か
- [ ] Queryが必要か
- [ ] DTOが必要か
- [ ] Resultが必要か
- [ ] Repository abstractionが必要か
- [ ] Unit of Workが必要か
- [ ] Identity Contextが必要か
- [ ] Domain Eventが必要か
- [ ] BusやHandlerへ分割する必要があるか

### 抽象化の確認

- [ ] 抽象化する具体的な理由があるか
- [ ] 実装差し替え・テスト・責務分離等の明確な効果があるか
- [ ] 将来の可能性だけを理由にしていないか
- [ ] 抽象化によってコードの理解が難しくなっていないか

---

## 16. AIへの対応手順

AIは、最初から大量のApplication部品を生成してはいけません。

### ステップ1：ユースケースを理解する

まず以下を確認します。

1. ユースケースの目的
2. 入力
3. 出力
4. 状態変更の有無
5. 必要なDomainモデル
6. 必要な外部・永続化処理
7. トランザクション境界
8. エラーケース

### ステップ2：最小構成を提案する

最初に、**最小限の具体実装**を提案します。

例：

~~~text
register_member()
    ↓
Member.register()
    ↓
repository.save()
~~~

必要がなければ、Command / Query / DTO / Result / UoW / Bus等を追加しません。

### ステップ3：複雑さを確認する

以下のような問題がある場合のみ、分割・抽象化を提案します。

- 1つの処理が長くなった
- 複数の責務が混ざった
- 同じ処理が複数箇所に現れた
- 実装差し替えが必要になった
- テストが困難になった
- Transaction境界を明示する必要が出た
- 外部技術への依存が広がった
- VSAの1スライスだけでは理解しにくくなった

### ステップ4：採用理由を説明する

新しい部品や抽象を追加する場合は、

- **なぜ必要なのか**
- **何が改善されるのか**
- **追加しない場合の問題は何か**

を説明します。

「DDDだから」「一般的だから」だけでは採用理由として不十分です。

### ステップ5：実装する

合意した最小構成を実装します。

Domainの業務ルールをApplicationへコピーせず、必要以上に抽象化しません。

---

## 17. 最終原則

> **Application層は、ユースケースを実現するために必要な最小限の構造で実装する。**
>
> **Domainのルールとアーキテクチャ上の境界は厳格に守る。**
>
> **一方で、Command、Query、DTO、Repository、Unit of Work、Bus等の具体的な実装手段は固定しない。**
>
> **小さく始め、複雑になったら分割し、必要になったら抽象化する。**

この方針により、DDDの重要な境界を守りながら、小規模なスクリプトから比較的複雑なアプリケーションまで、同じSeedworkを段階的に成長させられる構成を目指します。
