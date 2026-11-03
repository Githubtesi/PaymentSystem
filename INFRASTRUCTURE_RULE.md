# インフラストラクチャ層選定・実装ガイドライン

## 1. 役割

Infrastructure層は、**Domain / Applicationと、DB・外部API・ファイル・キャッシュ等の技術を接続する層**です。

主に次のような技術的関心事を扱います。

- データベース / ORM
- Repositoryの具体実装
- トランザクション
- 認証・実行コンテキストの具体実装
- 外部API / メッセージング / ファイル / キャッシュ
- 技術固有の例外
- 設定や接続管理

Infrastructure層に業務ルールを実装してはいけません。

### 重要な方針

Infrastructureでは、**必要な技術だけを必要な場所に実装する**ことを基本とします。

Repository、Unit of Work、Identity Context、Adapter、DI等は、すべての機能で必須ではありません。

> **Infrastructureも最小構成から始め、必要になったら分離・抽象化する。**

Infrastructureの責務とアーキテクチャ上の境界は守りますが、具体的な実装パターンは固定しません。

---

## 2. Infrastructure層で守るべき境界

### 必ず守ること

- 業務ルールをInfrastructureへ移さない。
- DB・ORM・外部SDK等の技術詳細を、必要以上にDomainへ漏らさない。
- Feature固有の技術実装をseedworkへ無秩序に追加しない。
- 技術固有のエラーとDomain / Applicationのエラーを混同しない。
- 外部システムとのデータ変換が必要な場合は、適切な境界で変換する。
- 秘密情報や接続情報をコードへハードコードしない。

### 実装方法について

Infrastructureの実装方法は、機能の規模や複雑さに応じて選択します。

小さな機能では単純な具体実装で十分な場合があります。

複数の実装を差し替える必要が出たり、技術依存が広がったりした場合に、Adapter、Interface、Repository abstraction等への分離を検討します。

---

## 3. 部品の選定基準

| 部品 | 採用 | 主な理由 |
| :--- | :--- | :--- |
| Database | 必要に応じて | DBを利用する |
| Repository Implementation | 必要に応じて | 永続化処理をRepositoryとして分離したい |
| Unit of Work Implementation | 必要に応じて | 複数操作のトランザクションを明示したい |
| Identity Context Implementation | 必要に応じて | 実行主体をApplicationへ渡す必要がある |
| External Adapter | 必要に応じて | 外部APIやSDKとの境界を分離したい |
| Infrastructure Exception | 必要に応じて | 技術エラーを整理する必要がある |
| DI | 必要に応じて | 依存関係の組み立てを外部へ分離したい |
| Mapping | 必要に応じて | Domainモデルと技術モデルの形式が異なる |

### 判断の原則

「Infrastructureの一般的な構成だから」ではなく、

> **この部品を追加することで、現在の技術的な複雑さや依存関係が管理しやすくなるか**

で判断します。

---

## 4. 具体実装を優先する

小規模な機能では、まず具体実装から始めます。

例えばDBアクセスが単純であれば、最初から複数のRepository InterfaceやAdapterを作る必要はありません。

    Use Case
       ↓
    Concrete Repository
       ↓
    DB

機能が成長して、具体実装への依存が問題になったら分離します。

    Application
       ↓
    Repository abstraction
       ↑
    Concrete Repository
       ↓
    DB

さらに外部API等との境界が複雑になった場合にAdapterを導入します。

### 抽象化の理由として有効なもの

- 実装を差し替える必要がある
- テストで置き換える必要がある
- 複数の技術実装が存在する
- Domain / Applicationへの技術依存が広がっている
- Mappingや変換処理が複雑になった
- 同じ技術的処理が複数Featureにまたがっている
- トランザクション等の技術的責務を明確にする必要がある

### 避ける理由

以下だけを理由に抽象化しません。

- 「DDDだから」
- 「Clean Architectureだから」
- 「Repositoryは必ずInterfaceにするものだから」
- 「将来DBを変更するかもしれないから」
- 「Interfaceがあった方が綺麗だから」

---

## 5. Repository実装

Repositoryを採用する場合、その具体実装はInfrastructureに配置します。

    Domain / Application
            ↓
    Repository abstraction
            ↑
    Infrastructure Repository
            ↓
    DB / ORM

### Repository実装で守ること

- Domain EntityへDB Modelを漏らさない。
- ORM Session等の技術オブジェクトをDomainへ渡さない。
- DB固有の処理をDomainへ持ち込まない。
- Repositoryへ業務ルールを実装しない。

### Mapping

Domain EntityとDB Modelが異なる場合は、MappingをInfrastructure内に閉じ込めます。

    Domain Entity
         ↓
    Infrastructure Mapping
         ↓
    DB Model

ただし、単純なケースで別のDB Modelが不要なら、無理にMapping層を作る必要はありません。

---

## 6. Unit of Work

Unit of Workは、**トランザクション境界を明示する必要がある場合に採用**します。

    Application
        ↓
    Unit of Work
        ↓
    DB Transaction

複数のRepository操作を1つのトランザクションとして扱う必要がある場合などに有効です。

一方、単純な1回のDB操作で既存のDBライブラリやFrameworkのトランザクション管理で十分なら、独自のUnit of Workを追加する必要はありません。

採用する場合は、具体的なSession / Transaction管理をInfrastructureに閉じ込めます。

---

## 7. Database

DBを利用する場合、接続・Session・Engine等の技術詳細はInfrastructure側で管理します。

例えばSQLAlchemyを使う場合、通常は以下をInfrastructureへ閉じ込めます。

- create_engine()
- sessionmaker()
- Session
- 接続URL
- Pool設定
- DB固有設定

ただし、既存Frameworkがこれらを管理している場合は、その仕組みをそのまま利用して構いません。

**同じ責務を独自のDatabase abstractionとして二重に作らないこと**を優先します。

---

## 8. Identity Context

認証情報や実行主体がApplicationに必要な場合、Infrastructure / Presentation側で具体的なIdentityを取得します。

    HTTP / Batch / CLI / Test
              ↓
    具体的Identity取得
              ↓
    Application

必要な場合は IIdentityContext 等の抽象を利用できます。

ただし、単純なアプリケーションで実行主体の取得方法が明確であり、抽象化によるメリットが小さい場合は、無理にIdentity Contextを作りません。

---

## 9. Infrastructure Exception

技術的な失敗をApplicationやDomainの業務エラーと区別する必要がある場合、Infrastructure Exceptionを利用します。

例:

| 例外 | 用途 |
| :--- | :--- |
| InfrastructureException | Infrastructure共通例外 |
| DatabaseConnectionError | DB接続失敗 |
| MappingError | モデル変換失敗 |
| ExternalServiceError | 外部サービスとの通信・応答エラー |

ただし、既存の例外体系で十分なら、Infrastructure固有の例外を増やす必要はありません。

### 基本的な区別

- **Domain Exception**: 業務ルール違反
- **Application Exception**: ユースケース上のエラー
- **Infrastructure Exception**: DB・ORM・外部サービス等の技術エラー

---

## 10. 業務ロジック禁止

Infrastructureに業務ルールを実装しないでください。

例えば、

    「金額がマイナスになってはいけない」

はDomainの責務です。

InfrastructureのRepositoryやAdapterは、原則として

    保存
    取得
    変換
    通信
    トランザクション

等の技術的責務を担当します。

ただし、DBの制約や外部サービスの仕様など、**技術的に必要な制約**はInfrastructureに存在して構いません。

---

## 11. 外部サービス連携

外部API、メール、メッセージング、ストレージ、決済サービス等を利用する場合、その技術詳細をInfrastructureで扱います。

    Application
         ↓
    必要に応じて抽象
         ↑
    Infrastructure Adapter
         ↓
    外部API / SDK

外部SDKの型をDomainへ直接持ち込むことは避けます。

ただし、小規模な処理で直接利用しても境界が崩れない場合は、最初からAdapterを作る必要はありません。

### Adapterを検討するタイミング

- SDKへの依存が複数箇所へ広がった
- テストで差し替える必要が出た
- 外部サービスを変更する可能性が具体化した
- 外部データの変換処理が複雑になった
- Domain / ApplicationへSDKの型が漏れ始めた

---

## 12. Dependency Injection

DIは**必要な場合に利用**します。

小規模な処理では、単純なコンストラクタ引数や関数引数で依存を渡すだけでも十分です。

    use_case = RegisterMember(repository)

依存関係が増えた場合はComposition RootやDIコンテナ等を検討します。

    Composition Root
           ↓
       Use Case
           ↓
    Infrastructure

DIコンテナ自体を導入することを目的にしないでください。

---

## 13. VSAとの関係

本プロジェクトではInfrastructureも**Feature単位で近くに配置することを優先**します。

例えば、

    src/
    ├── seedwork/
    ├── shared_kernel/
    └── features/
        └── member_management/
            ├── register_member.py
            ├── find_member.py
            └── ...

必要になった場合だけ、Feature内を分割します。

    member_management/
    └── register_member/
        ├── use_case.py
        ├── repository.py
        ├── models.py
        └── ...

さらに共通化できる技術基盤だけを src/seedwork/infrastructure/ へ移します。

### Seedworkへ入れる基準

- 複数Featureで実際に共有されている
- Feature固有の業務知識を含まない
- 技術基盤として再利用価値がある

「将来使うかもしれない」という理由だけでSeedworkへ追加しません。

---

## 14. 実装チェックリスト

### 必須確認

- [ ] 技術的責務であり、業務ルールではないか
- [ ] Domain / Applicationとの境界を意識しているか
- [ ] 技術依存が必要以上に内側へ漏れていないか
- [ ] Feature固有実装を無理にseedworkへ入れていないか
- [ ] 秘密情報や接続情報をハードコードしていないか

### 必要に応じて確認

- [ ] Repositoryが必要か
- [ ] Mappingが必要か
- [ ] Unit of Workが必要か
- [ ] Identity Contextが必要か
- [ ] Adapterが必要か
- [ ] Infrastructure Exceptionが必要か
- [ ] DIが必要か

### 抽象化の確認

- [ ] 抽象化する具体的な理由があるか
- [ ] テスト・交換・責務分離等の明確な効果があるか
- [ ] 将来の可能性だけを理由にしていないか
- [ ] 抽象化によって理解が難しくなっていないか

---

## 15. AIへの対応手順

AIは、Infrastructureの一般的なテンプレートをそのまま生成してはいけません。

### ステップ1：必要な技術を確認する

まず以下を確認します。

1. 使用するDB / 外部サービス
2. 必要な永続化処理
3. 必要な外部通信
4. トランザクション要件
5. 認証・実行主体の取得方法
6. 技術固有のエラー
7. 既存の共通基盤

### ステップ2：最小構成を提案する

最初に、必要最低限の具体実装を提案します。

例えばDB保存だけなら、

    Use Case
       ↓
    Concrete Repository
       ↓
    DB

程度から開始します。

Repository abstraction、UoW、Adapter、DI等は、必要性を確認してから追加します。

### ステップ3：複雑さを確認する

以下の問題がある場合に、分割・抽象化を提案します。

- 同じ技術処理が複数箇所に現れた
- 技術依存がApplication / Domainへ広がった
- テストで差し替えにくい
- 外部サービスの変換処理が複雑になった
- トランザクション境界が複雑になった
- 複数の実装を切り替える必要が出た
- Feature内のInfrastructureが大きくなった

### ステップ4：採用理由を説明する

新しい部品や抽象を追加する場合は、

- **なぜ必要なのか**
- **何が改善されるのか**
- **追加しない場合に何が問題になるのか**

を説明します。

「DDDだから」「一般的だから」だけでは採用理由として不十分です。

### ステップ5：実装する

合意した最小構成を実装します。

Infrastructureの技術詳細をDomainへコピーせず、必要以上に共通化・抽象化しません。

---

## 16. 最終原則

> **Infrastructure層は、技術的な責務を閉じ込める。**
>
> **Domainの業務ルールとApplicationのユースケース責務はInfrastructureへ移さない。**
>
> **一方で、Repository、Unit of Work、Adapter、DI等の実装パターンは固定しない。**
>
> **小さく具体的に始め、複雑になったら分割し、必要になったら抽象化する。**
>
> **VSAではFeatureの近くに実装し、実際に共有される技術基盤だけをSeedworkへ昇格させる。**

この方針により、Infrastructureを「最初から大規模な技術基盤として設計する層」ではなく、**Featureを実現するための技術的な境界として、必要な分だけ成長させる層**として扱います。
