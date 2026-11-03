# アーキテクチャ設計・実装ガイドライン

## 1. 目的

本ドキュメントは、プロジェクト全体のアーキテクチャ、依存方向、レイヤー境界、モジュール境界を定義する。

個々のレイヤーの詳細な設計ルールは、以下のドキュメントで定義する。

- `DOMAIN_RULE.md`
- `APPLICATION_RULE.md`
- `INFRASTRUCTURE_RULE.md`
- `MODULE_RULE.md`

本ドキュメントは、それらのルールより上位に位置する**プロジェクト全体のアーキテクチャルール**として扱う。

---

## 2. アーキテクチャの基本方針

本プロジェクトでは、DDDとVertical Slice Architecture（VSA）を基本とする。

基本的な責務分離は以下の通り。

Presentation
     ↓
Application
     ↓
Domain

Infrastructure
     ↓
Domain / Application の抽象

各層は、自分より内側の責務を利用できるが、内側の層が外側の具体技術へ依存してはいけない。

基本原則は以下とする。

1. Domainは業務知識の中心とする。
2. Applicationはユースケースの手順を調整する。
3. Infrastructureは技術的な具体実装を担当する。
4. Presentationは外部との入出力を担当する。
5. Featureは業務機能単位で垂直に分割する。
6. SeedworkはDDD実装のための汎用基盤とする。
7. Shared Kernelは複数Featureで共有する業務概念を配置する。
8. Feature間の直接依存を避ける。
9. 依存方向を明確にし、技術詳細を内側へ漏らさない。

---

## 3. Entity / dataclassの実装ルール

Domain Entityは、属性値ではなく識別子（ID）によって同一性を判定する。`Entity` 基底クラスの `__eq__` / `__hash__` を維持するため、Entityをdataclassとして実装する場合は必ず `@dataclass(eq=False)` を指定する。

```python
@dataclass(eq=False)
class User(Entity[str]):
    name: str = ""
```

`@dataclass` のデフォルト（`eq=True`）を使用すると、サブクラス側で属性値による `__eq__` が生成され、基底クラスのIDベースの同一性判定が上書きされる。また、可変dataclassでは `__hash__` が無効化される場合がある。これはEntityの設計意図と矛盾するため禁止する。

基本ルール:
- [ ] Entityのdataclassは `eq=False`
- [ ] Entityの同一性はIDで判定する
- [ ] EntityのハッシュはIDを基準とする
- [ ] `name` 等の状態属性だけで同一性を判定しない

詳細なDomain実装ルールは `DOMAIN_RULE.md` に従う。

## 3. レイヤー構成

### 3.1 Domain
Domainは、システムが扱う業務上の意味、ルール、不変条件を表現する。

配置例:
features/member_management/domain

Domainに配置する代表的な要素:
- Entity
- Value Object
- Aggregate Root
- Domain Event
- Domain Service
- Specification
- Factory
- Policy
- Repositoryの抽象

詳細は `DOMAIN_RULE.md` に従う。

### 3.2 Application
Applicationは、ユーザー操作やシステム上のユースケースを実行するための手順を調整する。

配置例:
features/member_management/use_cases

Applicationに配置する代表的な要素:
- Use Case
- Application Service
- Command
- Query
- Query Handler
- DTO
- Result
- Unit of Workの利用
- Identity Contextの利用

ApplicationはDomainの業務ルールを再実装してはいけない。

詳細は `APPLICATION_RULE.md` に従う。

### 3.3 Infrastructure
Infrastructureは、Domain / Applicationが定義した抽象を具体的な技術へ接続する。

代表例:
- Database
- ORM
- Repositoryの具体実装
- Unit of Workの具体実装
- 外部API Adapter
- Message Broker Adapter
- File Storage
- Cache
- Identity Contextの具体実装
- 技術固有例外

共通して再利用する基盤実装は `src/seedwork/infrastructure/` に配置する。
Feature固有は `features/.../infrastructure/`。

詳細は `INFRASTRUCTURE_RULE.md` に従う。

### 3.4 Presentation
Presentationは、外部世界との入出力を担当する。
代表例:
- HTTP API
- CLI
- Web UI Adapter
- Controller
- Request / Response変換

基本:
HTTP Request -> Presentation -> Command / Query -> Application -> Domain

Presentationに業務ルールを実装してはいけない。

---

## 3.1 Version管理のアーキテクチャルール

Version管理は、**すべてのAggregateへ一律に適用しない**。同時更新による重要な変更の消失を検出する必要があるAggregateに限定して採用する。判断基準は更新頻度ではなく、**同時更新時の競合を検出する必要性**とする。

### Version管理を適用する判断基準

以下を確認する。

1. 複数の利用者・プロセスが同じAggregateを並行して更新する可能性があるか。
2. 古い状態による更新が、新しい重要な変更を意図せず上書きする可能性があるか。
3. 競合を検出した場合に、Use Caseとして失敗・再取得・再確認等の扱いが必要か。
4. Unique Constraint、Idempotency、Pessimistic Lock等の別方式だけで十分に保証できないか。

典型的に検討対象となるAggregateは Order、Account、Inventory、Reservation、Payment などだが、機能名だけで機械的に決めず、実際の同時更新シナリオに基づいて判断する。

読み取り専用、同時更新による上書きが問題にならない、更新主体が一意に制御されている、または別の競合制御で要件を満たせる場合は、Version管理を追加しない選択ができる。

### Version管理の責務分担

| 判断・責務 | Domain | Application | Infrastructure |
|---|---|---|---|
| Version管理が必要かの業務上判断 | ○ | 補助 | × |
| Versionを持つEntity / Aggregateのモデル化 | ○ | × | × |
| Transaction境界の調整 | × | ○ | 実装 |
| Version条件付きUPDATE等の具体実装 | × | 抽象を利用 | ○ |
| ORMのVersion機構 | × | × | ○ |
| Concurrency Conflictの技術的検出 | × | × | ○ |
| ConflictをUse Case上でどう扱うか | × | ○ | 技術例外を抽象化して提供 |

DomainはSQLAlchemy、SQL、Session、version_id_col等の具体技術を参照してはいけない。

### Version管理の実装ルール

- Version管理が必要なEntity / Aggregateは VersionedEntity または VersionedAggregateRoot を利用する。
- dataclassは必ず @dataclass(eq=False) とする。
- Versionの初期値は 1 とする。
- version はEntityのIDとは別のConcurrency管理値である。
- Entityの同一性・hashはIDを基準とし、Versionを含めない。
- increment_version() はDomain上で明示的にVersionを進める必要がある場合に限定する。
- 通常の永続化におけるVersion更新はInfrastructure / ORM側で管理する。
- DomainからSQLAlchemy等のORMやDB固有APIを呼び出してはいけない。

Infrastructureでは、Versioned ModelにSQLAlchemyの version_id_col を設定し、VersionedSQLAlchemyRepositoryを利用する。競合は ConcurrencyConflictError に変換して外部へ提供する。

基本形:

Domain Entity
  ↓ Mapping
Versioned SQLAlchemy Model
  ↓
UPDATE ... WHERE id = ? AND version = ?
  ↓
成功 → Version更新
失敗 → Concurrency Conflict

### VersionとTransactionの関係

- Transactionはユースケースの原子性を保証する。
- Versionは並行更新による競合を検出する。
- Version管理はTransaction境界の代替ではない。
- Conflict発生時はTransactionをRollbackしてUse Caseへエラーを返す。
- 自動RetryはUse Caseの性質を確認した上で明示的に設計する。

### Version管理レビュー・チェックリスト

- [ ] Version管理が必要な理由を説明できる
- [ ] 同時更新シナリオを具体的に説明できる
- [ ] 不要と判断した場合、その理由を説明できる
- [ ] VersionをEntityのIDと混同していない
- [ ] VersionをEntityの同一性判定に使用していない
- [ ] DomainがSQLAlchemy等へ依存していない
- [ ] Version管理の具体実装がInfrastructureにある
- [ ] Repositoryが競合を検出できる
- [ ] ConcurrencyConflictErrorへ適切に変換される
- [ ] TransactionとConcurrency Controlの責務が混同されていない
- [ ] Conflict時のRollback / Retry方針が明確
- [ ] 全Aggregateへ不要にVersion管理を適用していない

## 4. 依存方向

### 4.1 基本ルール
Presentation -> Application -> Domain
Infrastructure -> Domain / Applicationの抽象

Infrastructureは外側から具体実装を提供する。

### 4.2 許可される依存
| From | To | 判定 |
|---|---|---|
| Presentation | Application | ○ |
| Application | Domain | ○ |
| Infrastructure | Domain | ○ |
| Infrastructure | Applicationの抽象 | ○ |
| Feature | Seedwork | ○ |
| Feature | Shared Kernel | ○ |

### 4.3 禁止される依存
| From | To | 判定 |
|---|---|---|
| Domain | Application | × |
| Domain | Infrastructure | × |
| Domain | Presentation | × |
| Application | Infrastructureの具体実装 | × |
| Application | Presentation | × |
| Seedwork | Feature | × |
| Seedwork | Shared Kernel | × |
| Shared Kernel | Feature | × |
| Feature A | Feature B | × |

---

## 5. 依存性逆転

Infrastructureなどの外側の具体実装をApplication / Domainから直接参照してはいけない。

Repository:
Domain -> IRepository <- Infrastructure -> SQLAlchemy

DomainはRepository等の抽象を定義し、Infrastructureが具体実装する。
これによりDomain / ApplicationはSQLAlchemy等の技術に依存しない。

---

## 6. 技術依存の境界

以下の具体技術はInfrastructureへ閉じ込める:
- SQLAlchemy
- Database Driver
- HTTP Client
- 外部API SDK
- Message Broker SDK
- Cloud SDK
- File System API
- Cache Client
- Authentication Framework

DomainからSQLAlchemyをimportしてはいけない。
ApplicationからSQLAlchemy Session等を直接利用してはいけない。
ApplicationはRepositoryやUnit of Work等の抽象を利用する。

---

## 7. Domain Modelと永続化モデルの分離

Domain EntityとDatabase Modelは別物として扱う。

Domain Entity -> Mapping -> Database Model -> SQLAlchemy
逆方向も同様。

MappingはInfrastructureに閉じ込める。
Domain EntityにSQLAlchemy Modelを直接保持させない。
Domain EntityからSQLAlchemy Sessionを直接利用しない。

---

## 8. Seedworkの境界

`src/seedwork/` はDDD実装のための汎用基盤。

配置してよい:
- Entity基底クラス
- Value Object基底クラス
- Aggregate Root基底クラス
- Repository抽象
- Domain Event基盤
- Application Service基底クラス
- Command / Query基盤
- Unit of Work抽象
- Infrastructure共通基盤

配置してはいけない:
- Member
- Order
- Invoice
- Customer
- Product
など特定業務機能のモデル。

---

## 9. Shared Kernelの境界

`src/shared_kernel/` は複数Featureで共有する具体的な業務概念を配置。

Feature A -> Shared Kernel <- Feature B

Shared KernelはFeatureへ依存しない。
特定Feature専用の業務ロジックをShared Kernelへ追加しない。
「共有したい」だけで移動せず、複数Featureにまたがる明確な共有責務がある場合のみ検討。

---

## 10. Feature境界

VSAを採用。

src/
├── seedwork/
├── shared_kernel/
└── features/
    ├── member_management/
    ├── order_management/
    └── ...

各Featureは可能な限り自己完結。
feature/
├── domain/
├── use_cases/
├── infrastructure/
└── presentation/

Feature AからFeature Bの内部モデルを直接参照しない。
別Feature連携は原則:
1. ID
2. Domain Event
3. Shared Kernel
4. 必要に応じた明示的Application境界

---

## 11. Feature間連携

内部モデルを直接公開しない。
例:
Order Feature -> Member ID -> Member Feature

またはDomain Event:
Member Feature -> MemberRegistered -> Subscriber in another feature

Feature間の直接importで内部構造を共有しない。

---

## 12. 業務ルールの配置

Domain: 「何が正しいか」
Application: 「何をどの順番で実行するか」
Infrastructure: 「どの技術を使って実現するか」
Presentation: 「外部からどう受け取り、どう返すか」

迷った場合はこの4つの問いを使う。

---

## 13. トランザクション境界

業務的なトランザクション境界はApplicationが調整し、具体的DBトランザクションはInfrastructureが実装。

Application -> IUnitOfWork <- Infrastructure -> SQLAlchemy Session

Applicationは `with unit_of_work:` のように抽象を利用する。

---


---

## 14. Transaction / Concurrency

トランザクションと同時実行制御は、**Applicationが境界を決め、Infrastructureが具体的な仕組みを実装する**。

### 14.1 Transaction Boundary

1つのユースケースで、どこまでを原子的に成功・失敗させるかをApplicationが決定する。

基本形:

Application Use Case
    ↓
IUnitOfWork
    ↓
Repository
    ↓
Infrastructure / Database

ApplicationはDBのTransaction APIやSQLAlchemy Sessionを直接操作してはいけない。

ApplicationはUnit of Workの抽象を利用し、実際のTransaction開始・Commit・RollbackはInfrastructureが担当する。

### 14.2 Transaction Boundaryの原則

- 原則として1つのUse Caseを1つのTransaction境界として扱う。
- Transactionの開始・Commit・RollbackをDomainに置かない。
- Domain Entity / Value ObjectからDB Transactionを操作しない。
- Applicationは「何を1つの原子操作として扱うか」を決定する。
- Infrastructureは「その原子操作をどのDB機構で実現するか」を決定する。
- 外部API呼び出しやMessage Broker送信を、DB Transactionの単純な一部として扱わない。
- 長時間Transactionを避け、Transaction内の処理を必要最小限にする。

### 14.3 Commit / Rollback

Applicationは正常終了時にCommitし、例外発生時にはRollbackされる構造を利用する。

```text
Use Case
  ↓
Begin Transaction
  ↓
Load Aggregate
  ↓
Domain Logic
  ↓
Persist Changes
  ↓
Commit
```

失敗時:

```text
Use Case
  ↓
Begin Transaction
  ↓
...
  ↓
Exception
  ↓
Rollback
```

Commit済みの処理をApplicationが再度取り消すことをRollbackと混同しない。

### 14.4 TransactionとDomain Event

Domain Eventの発生とDB更新の整合性を考慮する。

基本方針:

```text
Domain
  ↓
Domain Eventを生成
  ↓
Application
  ↓
Transaction内でAggregate変更を保存
  ↓
Infrastructure
  ↓
必要に応じてOutboxへ保存
  ↓
Commit
  ↓
非同期配送
```

DB更新と外部Message Brokerへの直接送信を、同一Transactionとして保証できない場合はOutbox Patternを検討する。

Domain EventそのものにMessage BrokerやDBの具体技術を持たせない。

### 14.5 Concurrency Control

同時実行制御は、データ競合による意図しない上書きを防ぐために行う。

代表的な方式:

- Optimistic Locking
- Pessimistic Locking
- DatabaseのUnique Constraint
- DatabaseのForeign Key / Constraint
- Idempotency

原則として、**業務上の競合を検出するルール**と**DB上で競合を検出する技術**を分離する。

### 14.6 Optimistic Locking

通常はOptimistic Lockingを第一候補とする。

AggregateにVersion等のConcurrency Tokenを持たせ、更新時に取得時のVersionと一致することを確認する。

```text
Read:
  id = 100
  version = 3

Update:
  UPDATE ...
  WHERE id = 100
    AND version = 3

Success:
  version = 4

Conflict:
  更新件数 = 0
  → Concurrency Conflict
```

Version管理の具体的なSQLAlchemy実装はInfrastructureに置く。

Optimistic Lockingを実装するRepositoryは、更新時に取得時のVersionを条件へ含め、更新件数が0件なら `ConcurrencyConflictError` へ変換する。Versionを利用するEntity / Modelでは、Versionの初期値とインクリメント規則を明確にする。

ApplicationはConcurrency Conflictをユースケース上のエラーとして扱える抽象を利用する。

競合発生時に自動Retryしてよいかは、Use Caseの性質を考慮して決定する。

### 14.7 Pessimistic Locking

同時更新を許可せず、処理中は対象データをロックする必要がある場合はPessimistic Lockingを利用できる。

例:

```text
SELECT ... FOR UPDATE
```

ただし、DomainやApplicationにSQL文やORM固有のLock APIを漏らしてはいけない。

必要な場合はRepository等の抽象を通じてInfrastructureへ委譲する。

### 14.8 Retry

Concurrency Conflictや一時的なDBエラーに対するRetryは、無条件に実装してはいけない。

Retryを検討する条件:

- 操作が再実行可能である
- 副作用が重複しない
- Transactionを再開始できる
- 最大Retry回数を設定できる
- Backoff等を考慮できる

特に外部API送信、メール送信、決済等の副作用を含むUse Caseでは、単純なRetryによる二重実行に注意する。

### 14.9 Idempotency

外部から同じCommandが複数回送信される可能性がある場合、必要に応じてIdempotencyを設計する。

例:

```text
Command
  + Idempotency Key
        ↓
Application
        ↓
Idempotency Check
        ↓
Use Case
        ↓
Transaction
```

Idempotency Keyの保存・一意制約などの具体実装はInfrastructureで行う。

「Retryできる」ことと「Idempotentである」ことは同じではない。

### 14.10 Database Constraint

競合防止や不変条件の一部はDatabase Constraintでも保証する。

例:

- UNIQUE
- PRIMARY KEY
- FOREIGN KEY
- CHECK

ただし、Database Constraintだけに業務ルールを依存してはいけない。

Domainが表現すべき業務ルールはDomainでも表現し、Database Constraintは永続化層での最終防衛線として利用する。

### 14.11 Transactionと外部システム

DB Transactionの中で、以下の外部処理を長時間実行しない。

- HTTP API
- 外部サービス
- Message Broker
- メール送信
- ファイルアップロード

必要な場合は以下を検討する。

- Outbox Pattern
- Inbox Pattern
- Saga / Process Manager
- 非同期Job

ただし、導入は必要性が明確な場合に限定する。

### 14.12 Transaction / Concurrencyの責務分担

| 判断対象 | Domain | Application | Infrastructure |
| :--- | :--- | :--- | :--- |
| 業務上の不変条件 | ○ | × | × |
| Transaction境界の決定 | × | ○ | 実装 |
| Commit / Rollback | × | 抽象を利用 | ○ |
| Unit of Work抽象 | 必要に応じて | ○ | 具体実装 |
| Optimistic Lockの具体実装 | × | 抽象を利用 | ○ |
| Pessimistic Lockの具体実装 | × | 抽象を利用 | ○ |
| DB Constraint | × | × | ○ |
| Retry方針 | × | ○ | 技術的Retry |
| Idempotencyのユースケース方針 | × | ○ | 永続化実装 |
| Outbox | × | 発行・調整 | ○ |

### 14.13 AI実装時のConcurrency確認

AIはTransactionやConcurrencyに関するコードを追加・変更する前に、以下を確認する。

1. そのUse CaseのTransaction境界を確認する。
2. 既存のUnit of Work抽象を確認する。
3. Repositoryの取得・保存方法を確認する。
4. Version / Concurrency Tokenの有無を確認する。
5. 既存のRetry方針を確認する。
6. Idempotencyが必要か確認する。
7. Domain Event / Outboxとの整合性を確認する。
8. DB Constraintとの責務重複を確認する。
9. SQLAlchemy等の具体技術をDomain / Applicationへ漏らさない。
10. 新しいTransaction管理方式を既存設計と矛盾した形で勝手に追加しない。

### 14.14 Transaction / Concurrencyレビュー・チェックリスト

- [ ] Use Case単位のTransaction境界が明確
- [ ] Transactionの具体実装がInfrastructureにある
- [ ] DomainがTransactionを操作していない
- [ ] ApplicationがDB Session等を直接操作していない
- [ ] Commit / Rollbackの責務が明確
- [ ] 同時更新時の競合戦略が明確
- [ ] Optimistic / Pessimistic Lockの選択理由が明確
- [ ] Retryによる二重実行が発生しない
- [ ] 必要なIdempotencyが設計されている
- [ ] Database Constraintを適切に利用している
- [ ] Domain EventとDB更新の整合性を確認している
- [ ] 必要に応じてOutbox Patternを検討している
- [ ] 外部API等を長時間Transactionに巻き込んでいない
- [ ] SQLAlchemy等の技術詳細が内側へ漏れていない

## 14. Domain Eventの境界

Domain Eventの「何が起きたか」はDomainが定義。
発行・配送の調整はApplication。
Message Broker等の具体技術はInfrastructure。

---

## 15. Identityの境界

HTTP / Batch / Test -> Concrete Identity Context -> IIdentityContext -> Application

Application / DomainからFastAPI、HTTP Request等の具体オブジェクトを直接参照しない。

---

## 16. 配置判断フロー

① DDD実装の汎用基盤か? -> Seedwork
② 複数Featureで共有する具体的業務概念か? -> Shared Kernel
③ 特定Featureの業務知識か? -> Feature / Domain
④ ユースケースの手順・調整か? -> Feature / Application
⑤ DB・外部API・SDK等の具体技術か? -> Feature / Infrastructure
⑥ HTTP/API/UI等の外部接続か? -> Feature / Presentation

---

## 17. AIによる実装時の対応手順

AIはコード作成・変更前に:
1. Architecture Rule確認
2. MODULE_RULE確認
3. Layer判断
4. 該当Layer Rule確認
5. 既存コード確認
6. 依存方向確認
7. 実装
8. 最終確認

既存の抽象、基底クラス、Repository、Domain Event、Unit of Work、Feature、Mapping、依存関係を確認し、既存設計と矛盾する新しい仕組みを勝手に追加しない。

最終確認:
- Layer依存方向
- Domainへの技術依存漏れ
- Applicationへの業務ルール漏れ
- Infrastructureへの業務ルール漏れ
- Presentationへの業務ルール漏れ
- Feature間直接依存
- SeedworkへのFeature固有コード追加
- Shared Kernelへの不要なFeature固有コード追加
- Domain Entity / DB Model分離
- 外部SDK型の漏出
- 既存Ruleとの矛盾

---

## 18. 禁止事項

- DomainからInfrastructureへの依存
- DomainからApplicationへの依存
- ApplicationからInfrastructure具体実装への依存
- Feature間直接依存
- SeedworkからFeatureへの依存
- Shared KernelからFeatureへの依存
- Presentationへの業務ルール実装
- Infrastructureへの業務ルール実装

業務上の意味を持つ判断はDomainへ配置する。

---

## 19. Architectureレビューのチェックリスト

### Layer
- Domain / Application / Infrastructure / Presentationの責務が明確
- 各処理が適切なLayer
- Layer間依存方向が正しい

### Module
- Seedworkに業務固有コードなし
- Shared Kernelに不要な共有コードなし
- Feature境界が明確

### Dependency
- Domain -> Applicationなし
- Domain -> Infrastructureなし
- Application -> Infrastructure具体実装なし
- Feature間直接依存なし
- 外部技術が内側へ漏れない

### Domain
- 業務ルールがDomain
- Entity / VO / Aggregate等の責務が明確

### Application
- ユースケース調整に集中
- Domainルール再実装なし
- Repository / UoW等の抽象を利用

### Infrastructure
- Repository等の具体実装がInfrastructure
- MappingがInfrastructure
- DB / ORM / SDKが内側へ漏れない

### Presentation
- 入出力変換に集中
- 業務ルールなし
- Application経由でユースケース実行

---

## 20. 最終原則

業務知識は Domain に置く。
ユースケースの手順は Application に置く。
技術的な実装は Infrastructure に置く。
外部との入出力は Presentation に置く。
DDDの汎用基盤は Seedwork に置く。
複数Featureで共有する業務概念は Shared Kernel に置く。
Featureは業務機能単位で独立させる。
依存方向を制御し、内側へ技術詳細を漏らさない。

判断に迷った場合は、
「これは業務上の意味なのか、処理の手順なのか、技術的な実装なのか、外部との接続なのか」
を基準として配置を決定する。

既存のRuleと矛盾する場合は、まずArchitecture上の責務境界を確認し、その後に各LayerのRuleを適用する。


---

## 21. 具体化を優先し、必要になったら抽象化する

本プロジェクトでは、**最初からRepositoryやInterface等の抽象を過剰に導入しない**。

小規模なFeatureやスクリプトでは、まず具体的な実装でシンプルに構築し、実際に抽象化が必要になった時点で導入する。

これは「RepositoryやInterfaceを使用しない」という意味ではない。  
**抽象化を目的にしない**という意味である。

### 21.1 基本原則

原則として以下の順序で設計する。

```text
具体的な実装
    ↓
実際の要件・複雑性を確認
    ↓
抽象化が必要か判断
    ↓
必要な場合のみInterface / Protocol / Repository等を導入
```

最初から以下を機械的に追加してはいけない。

- Repository Interface
- Repository Implementation
- Application Service Interface
- Infrastructure Adapter Interface
- Factory
- Unit of Work
- その他の抽象レイヤー

### 21.2 抽象化を導入する判断基準

以下のいずれかに明確な必要性がある場合、抽象化を検討する。

1. **依存方向を守る必要がある**
   - Domain / ApplicationからInfrastructureの具体実装を参照させたくない。
2. **実装を差し替える必要がある**
   - Database、外部API、File Storage等に複数の実装が存在する、または将来の差し替えが具体的に想定される。
3. **テスト上の差し替えが必要である**
   - 実際の外部システムを使わずにUse Caseを検証する必要がある。
4. **複数の利用者から共通の契約が必要である**
   - 実装詳細ではなく、利用側が必要とする振る舞いを明確な契約として定義する必要がある。
5. **複雑性を局所化できる**
   - 抽象化によって技術詳細を閉じ込め、FeatureやDomainの理解を容易にできる。
6. **既存のDomain Rule / Architecture Ruleを守るために必要である**
   - 具体実装を直接参照すると、依存方向や責務境界を破る場合。

単に「DDDではRepositoryを使う」「Clean ArchitectureではInterfaceを使う」といった理由だけで導入してはいけない。

### 21.3 Repositoryの扱い

Repositoryは、**必要な場合にDomain / Applicationと永続化技術の境界を作るために使用する**。

以下のような単純な処理では、Repositoryを必須としない。

- 単純なスクリプト
- 単純な読み取り処理
- 抽象化によるメリットがない小規模な処理
- 永続化方式が単純で、依存方向上も問題がない処理

一方、Domainから永続化の詳細を隠す必要がある場合、複数の永続化実装を扱う場合、テストで差し替える必要がある場合などはRepositoryの導入を検討する。

Repositoryを導入する場合も、必要以上に細かいInterfaceやクラスを作成しない。

### 21.4 VSAとの関係

VSAでは、**Featureを最小限の構成から開始し、必要に応じてFeature内部を分割する**。

例:

```text
最初:

features/
└── create_user/
    └── create_user.py
```

複雑化した場合:

```text
features/
└── create_user/
    ├── command.py
    ├── handler.py
    └── repository.py
```

さらに必要になった場合にのみ、Infrastructure Adapterやその他の抽象を追加する。

最初から全Featureを同じファイル構成に揃えることを目的としない。

### 21.5 AIによる判断

AIはRepository、Interface、Factory、Unit of Work等を新規追加する前に、以下を確認する。

1. この抽象化が必要な具体的理由は何か。
2. 抽象化しない場合に、どのArchitecture Ruleへ違反するのか。
3. 差し替え対象となる実装が実際に存在するか。
4. テスト上の差し替えが本当に必要か。
5. 抽象化によってコード量・理解コストが増えないか。
6. VSAのFeature境界と整合しているか。
7. 既存の抽象を再利用できないか。
8. 同じ目的の抽象を重複して追加していないか。

明確な必要性がない場合は、**具体実装を維持する**。

### 21.6 禁止する考え方

以下を設計理由として抽象化を導入してはいけない。

- 「将来使うかもしれない」
- 「DDDだからRepositoryが必要」
- 「Interfaceがあるほうが綺麗」
- 「テストしやすそう」
- 「Architectureらしく見える」
- 「他のFeatureと構造を揃えたい」

将来の可能性だけを理由にした抽象化は、必要になった時点で追加する。

### 21.7 レビュー・チェックリスト

- [ ] まず具体実装で実現できないか確認した
- [ ] 抽象化を導入する具体的理由を説明できる
- [ ] Repositoryを必須部品として機械的に追加していない
- [ ] Interfaceを目的なく追加していない
- [ ] 将来の可能性だけを理由に抽象化していない
- [ ] 抽象化によるコード量・理解コストを確認した
- [ ] VSAのFeatureを不必要に分割していない
- [ ] 既存の抽象を再利用できないか確認した
- [ ] Domain / ApplicationからInfrastructure具体実装を参照する必要がある場合は、依存方向を再確認した
- [ ] 抽象化しない判断をした場合、その理由を説明できる

### 21.8 最終原則

> **具体化をデフォルトとし、必要になったら抽象化する。**

抽象化は「最初から用意する設計部品」ではなく、**実際の要件、依存方向、差し替え、テスト、複雑性によって必要性が明らかになったときに導入する設計手段**として扱う。

小規模な処理では、少ないファイル・少ない抽象・少ない依存で理解しやすい構造を優先する。
