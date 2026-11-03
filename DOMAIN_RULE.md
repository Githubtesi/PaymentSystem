# ドメイン選定・実装ガイドライン
## 1. 参照資料
ドメインモデルの検討および実装にあたっては、以下のドキュメントを「ガードレール」として最優先で参照すること。

必須資料: Domain Seedwork 復習ガイド.pdf

関連資料:
- `APPLICATION_RULE.md`
- `INFRASTRUCTURE_RULE.md`
- `MODULE_RULE.md`

## 2. シードワーク選定フロー
AIは、検討対象の要素が以下のどの「部品」に該当するかを判断し、選定理由を提示してください。

## 3. 対話プロトコル
| 部品名 | 役割・特徴 | ファイルパス (`src/seedwork/domain/`) | ベースクラス名 |
| :--- | :--- |:--------------------------------| :--- |
| **Exceptions** | ルール違反を知らせるための独自エラー | `domain_exception.py` | `ValueObjectValidationError`, `DomainException` |
| **Value Object** | 中身が同じなら同じものとして扱う、不変のデータ | `value_object.py` | `ValueObject` |
| **Entity** | ID（背番号）で区別され、状態が変わっても同一性を保つもの | `entity.py` | `Entity` |
| **Aggregate Root** | 関連するデータの集まり（チーム）のキャプテンであり、外部との窓口 | `aggregate_root.py` | `AggregateRoot` |
| **Repository** | データの保存や取り出しを行う際の「お願いの仕方」を定めた窓口 | `repository.py` | `Repository` |
| **Domain Event** | ドメイン内で発生した「重要な出来事」を知らせるためのお手紙 | `domain_event.py` | `DomainEvent` |
| **Domain Service** | 特定のEntityに任せるのが不自然な、審判のような計算や判断 | `domain_service.py` | `DomainService` |
| **Specification** | あるデータが合格基準を満たしているか判定するチェックリスト | `specification.py` | `Specification` |
| **Factory** | 複雑なEntityやAggregateを正しい初期状態で組み立てる専門の工場 | `factory.py` | `Factory` |
| **Policy** | 状況に応じて取り替え可能なビジネス上の「作戦」や計算の方針 | `domain_policy.py` | `DomainPolicy` |
| **Events** | 情報を発信する人（Publisher）と受け取って動く人（Subscriber）の仕組み | `domain_event.py` | `Publisher`, `Subscriber` |

### 実装上の重要注意点
* **アプリケーションサービス:** アプリケーションサービスはビジネスを動かす「手順」を記述するものです。
    * ドメイン層ではなく、「アプリケーション層」に配置する必要があります。
* **Value Objectの特性:** 一度決めたら内容を変えず、新しく作り直す「不変性」を持たせてください。
    * データ作成時に自らのルールを検証してください。
* **責務の分離:** Domain層は業務上の意味とルールを担当し、Application層はユースケースの手順を担当し、Infrastructure層は具体的な技術実装を担当してください。

## 3.1 Version管理の選定基準

Version管理は、**すべてのEntity / Aggregateに必須ではありません**。同時更新による意図しない上書きを検出する必要があるAggregateに限定して採用します。

### Version管理を検討する条件

以下のような場合はVersion管理を候補とします。

- 複数の利用者・プロセスが同じAggregateを並行して更新する可能性がある。
- 古い状態を新しい状態で上書きすると、業務上重要な変更が失われる。
- 更新競合を検出して、処理を失敗させたり再確認を促したりする必要がある。
- 「取得した時点の状態を前提として更新する」という業務上の意味がある。

典型例:
- Order: 注文状態・金額・明細などの同時更新
- Account: 残高・利用可能額などの同時更新
- Inventory: 在庫数量などの同時更新
- Reservation: 予約枠・予約状態などの同時更新
- Payment: 決済状態などの同時更新

一方、以下はVersion管理が不要または優先度が低い場合があります。

- 読み取り専用のデータ
- 同時更新による上書きが業務上問題にならないデータ
- 更新主体が一意に制御され、競合が発生しないことを別の仕組みで保証できるデータ
- DBの一意制約など、Version以外の仕組みで十分に競合を検出できるケース

**判断基準は「更新頻度が高いか」ではなく、「同時更新による失われた変更を検出する必要があるか」です。**

### AIがVersion管理を選定するときの確認事項

1. Aggregateの同時更新が発生するか。
2. 競合による上書きが業務上問題になるか。
3. 競合を検出した場合のUse Case上の扱いが定義できるか。
4. Unique ConstraintやIdempotency等、別の競合対策で十分ではないか。
5. VersionをDomainの状態として公開する必要があるか。
6. 不要なAggregateへ一律にVersion管理を追加していないか。

## 3.2 Version管理の実装ルール

Version管理が必要なAggregateは、原則としてSeedworkのVersion管理基盤を利用します。

### Domain

- `VersionedEntity` または `VersionedAggregateRoot` を利用する。
- Entityのdataclassは必ず `@dataclass(eq=False)` とする。
- Versionの初期値は `1` とする。
- `version` はEntityの同一性を表すものではなく、Concurrency制御用の値として扱う。
- Entityの `__eq__` / `__hash__` は従来どおりIDを基準とし、Versionを同一性判定に含めない。
- Versionを利用するAggregateは、必要に応じてDomain上でVersionを参照できる。
- `increment_version()` はDomain上で明示的にVersionを進める必要がある場合に限って利用する。通常の永続化ではInfrastructure側のORM管理を基本とする。
- DomainからSQLAlchemyやDBのVersion機構を直接参照してはいけない。

例:

```python
from dataclasses import dataclass

from seedwork.domain.versioned_aggregate_root import VersionedAggregateRoot


@dataclass(eq=False)
class Order(VersionedAggregateRoot[str]):
    total: int = 0
```

### Versionのライフサイクル

基本的な流れ:

```text
取得
  ↓
version = 3
  ↓
Domain変更
  ↓
保存
  ↓
version = 4
```

古いVersionで保存した場合は競合として扱います。

```text
Process A: version = 3 を取得
Process B: version = 3 を取得

Aが更新 → version = 4

Bが version = 3 のまま更新
        ↓
Concurrency Conflict
```

Versionは通常、DB更新成功時にInfrastructureが進めます。DomainがVersionを手動更新する場合は、その責務とタイミングをUse Case / Domain設計で明確にします。

## 4. AIへの対応手順

### ステップ1：「〇〇に関するドメインを検討してください」への対応
1. Domain Seedwork 復習ガイド.pdf を読み込み、各部品の定義を再確認する。
2. 対象ドメインを分析し、どの概念を Entity, Value Object, Policy 等にするべきか提案する。
3. 関連するApplication / Infrastructureの責務と混同しないように境界を確認する。
4. 提案時の必須項目:
   - 選定したシードワーク名とその理由。
   - そのモデルが守るべき具体的なルール（例：「金額はマイナスを許容しない」等）。
   - Aggregateの境界と、外部から許可する操作。
   - 必要に応じてDomain Event、Repository、Specification、Policy等との関係。
   - Application層へ委譲する処理と、Infrastructure層へ委譲する処理。
   - Version管理が必要かどうか、その選定理由。

### ステップ2：「提案内容を元にドメインを作成してください」への対応
1. ステップ1で合意した構成に基づき、`src/seedwork/` のベースクラスを継承して実装する。
2. 実装の共通ルール:
   + クラス定義:
       - Value Objectは `@dataclass(frozen=True)` を付与し、`validate()` メソッドを実装する。
       - Entityは `@dataclass(eq=False)` を付与し、IDによる同一性判定を維持する。
       - Version管理が必要なEntity / Aggregateは `VersionedEntity` / `VersionedAggregateRoot` を利用し、VersionをIDと混同しない。
   + エラー処理: ルール違反時は `domain_exception.py` の `ValueObjectValidationError` 等を利用する。
   + カプセル化: Value Objectは不変とし、Entityの状態変更はメソッド経由で行う。
   + 配置:
       - `application_service.py` やユースケースはドメイン層ではなく、**「アプリケーション層」**に置くことを厳守する。
       - 各機能は `src/features/[機能名]/` 配下で垂直に切り分ける。

## 5. Application / Infrastructureとの境界確認
ドメインを実装する際、AIは以下を確認してください。

| 判断対象 | Domain | Application | Infrastructure |
| :--- | :--- | :--- | :--- |
| 業務ルール・不変条件 | ○ | × | × |
| Entity / Value Object | ○ | × | × |
| ユースケースの手順 | × | ○ | × |
| Command / Query | × | ○ | × |
| Repositoryの抽象 | ○ | 必要に応じて利用 | × |
| Repositoryの具体実装 | × | × | ○ |
| DB / ORM / SQLAlchemy | × | × | ○ |
| 外部API / SDK | × | × | ○ |
| Transactionの具体実装 | × | 抽象を利用 | ○ |
| Domain Eventの定義 | ○ | 発行・配送を調整 | 技術的配送を担当可能 |

判断に迷う場合は、**「その処理は業務上の意味を持つか」**を基準にしてください。業務上の意味・ルールであればDomain、ユースケースの手順であればApplication、具体的な技術接続であればInfrastructureを候補としてください。

## 6. 最終確認チェックリスト
AIはドメインの検討・実装後、以下を確認してください。

- [ ] 業務ルールがDomain層に配置されているか
- [ ] Application層へ業務ルールを流出させていないか
- [ ] Infrastructure層へ業務ルールを流出させていないか
- [ ] Entity / Value Object / Aggregate等の選定理由を説明できるか
- [ ] Aggregate境界が明確か
- [ ] Entityの状態変更がカプセル化されているか
- [ ] Value Objectが不変になっているか
- [ ] Repositoryの抽象と具体実装を分離できているか
- [ ] DBや外部API等の具体技術がDomainへ漏れていないか
- [ ] 必要なDomain Eventを適切に表現できているか
- [ ] Featureごとの配置ルールに従っているか
- [ ] Version管理の必要性を検討し、選定理由を説明できるか
- [ ] VersionをEntityの同一性（ID）と混同していないか
- [ ] Version管理が必要なAggregateだけに適用しているか
