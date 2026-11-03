# モジュール生成および配置ルール

## 1. 基本方針

本プロジェクトでは **Vertical Slice Architecture (VSA)** を基本とし、ビジネス機能（Feature）を中心にコードを配置します。

ただし、VSAのためにすべての機能を同じディレクトリ構成へ機械的に揃えることはしません。

基本原則は次のとおりです。

> **機能を近くに置く。必要なものだけ作る。複雑になったら分割する。**

- **境界は厳格に守る**
- **ディレクトリ構成や分割方法は柔軟にする**
- **小さな機能に過剰な階層を作らない**
- **具体的な実装を優先し、必要になったら抽象化・分割する**
- DDDのルールそのものは `DOMAIN_RULE.md` に従う
- Application / Infrastructure の実装方針は、それぞれのルールファイルに従う

---

## 2. ディレクトリの役割

### 2.1 `src/seedwork/`

DDDやアプリケーションを実装するための**汎用的な基盤**を配置します。

例：

- Entity
- Value Object
- Aggregate Root の基底機能
- Domain Event の基盤
- Repository の共通契約
- Unit of Work の共通基盤
- Result / Error など、複数機能で利用する技術的基盤

原則として、

- 特定の業務機能に依存しない
- 特定Featureの業務ルールを持ち込まない
- 「共通化できそう」という理由だけで配置しない

とします。

**Seedworkへ移す判断は、実際に複数箇所で共有され、基盤として安定している場合を基本とします。**

### 2.2 `src/shared_kernel/`

複数のFeatureが共有する**ドメイン上の概念**を配置します。

例：

- `Address`
- `Money`
- 共通のドメインポリシー
- 複数のBounded Context / Featureで共有するValue Object

ただし、単なる便利クラスや技術的ユーティリティを何でもShared Kernelへ入れてはいけません。

判断基準は、

> **「複数Featureで共有されるドメイン概念か？」**

です。

単なる技術的共通処理は `seedwork` または適切なInfrastructure/Application側へ配置します。

### 2.3 `src/features/`

ビジネス機能ごとの**垂直スライス（Vertical Slice）**を配置します。

例：

```text
src/
├── seedwork/
├── shared_kernel/
└── features/
    ├── member_management/
    ├── order/
    └── billing/
```

Featureは、可能な限りその機能に必要なコードを近くにまとめます。

ただし、すべてのFeatureが同じ構造である必要はありません。

---

## 3. Feature内部の構成

Feature内部の構成は**固定しません**。

例えば、複雑なFeatureでは次のように分割できます。

```text
features/
└── member_management/
    ├── domain/
    ├── application/
    ├── infrastructure/
    └── presentation/
```

一方、小さなFeatureでは、次のようにシンプルにして構いません。

```text
features/
└── member_management/
    └── register_member.py
```

また、ユースケース単位でまとめる構成も許容します。

```text
features/
└── member_management/
    ├── register_member/
    │   ├── handler.py
    │   └── repository.py
    └── deactivate_member/
        └── handler.py
```

重要なのはディレクトリの形ではなく、

- Featureの境界が明確であること
- Domainの業務ルールが守られていること
- Application / Infrastructure の責務が混ざらないこと
- 不要な抽象化や階層を増やさないこと

です。

---

## 4. Domain / Application / Infrastructure の配置

Feature内部では、必要に応じて各責務を分離します。

### Domain

業務ルール・不変条件・Aggregateなどを配置します。

```text
member_management/
└── domain/
    ├── member.py
    └── member_repository.py
```

ただし、Repositoryなどの抽象化を**必ず作る必要はありません**。

具体的な実装で十分な場合は、Application / Infrastructureのルールに従って最小構成とします。

### Application

ユースケースのオーケストレーションを配置します。

```text
member_management/
└── application/
    └── register_member.py
```

Command / Query / Handler / DTO / Resultなどは、必要な場合のみ追加します。

### Infrastructure

DB、ORM、外部API、ファイル、キャッシュなどの技術的実装を配置します。

```text
member_management/
└── infrastructure/
    └── member_repository.py
```

Repository実装、Unit of Work、Adapter、DIなども必要な場合のみ追加します。

### Presentation

API、CLI、画面など、外部からFeatureへ入る入口を配置します。

ただし、Featureが内部処理専用でPresentationを持たないことも許容します。

---

## 5. VSAの粒度

VSAの目的は、**関連する変更を近くに置き、変更の影響範囲を小さくすること**です。

そのため、Featureを細かく分割しすぎないようにします。

### 分割する目安

次のような状況ではFeatureやモジュールの分割を検討します。

- 1つのFeatureが大きくなった
- 複数のユースケースが独立して変更される
- 業務ルールの境界が明確に分かれた
- チームや担当者による変更範囲を分けたい
- テストや依存関係の管理が難しくなった

### 分割しない目安

次の理由だけでは分割しません。

- 「VSAだから」
- 「DDDだから」
- 「Clean Architectureだから」
- 「将来使うかもしれない」
- 「ディレクトリ構造がきれいになる」

---

## 6. Feature間の依存

Feature同士は、**他Featureの内部実装へ直接依存しない**ことを原則とします。

例えば、

```python
from features.member_management.domain.member import Member
```

のように、別FeatureのDomainモデルを直接利用することは避けます。

Feature間の連携が必要な場合は、状況に応じて次の方法を検討します。

1. IDなどの識別子を渡す
2. Domain Event / Application Eventを利用する
3. 明示的なApplication上の契約を利用する
4. 本当に共有すべきドメイン概念なら `shared_kernel` を検討する

ただし、単純な内部処理までイベント化する必要はありません。

**Feature間の境界を守ることが目的であり、特定の連携方式を強制することが目的ではありません。**

---

## 7. Shared Kernelへ移す基準

Feature内のコードをShared Kernelへ移す場合は、慎重に判断します。

次の条件を満たすほどShared Kernel候補になります。

- 複数Featureから実際に利用されている
- ドメイン上の意味を持つ
- 各Featureで独自実装するより共有した方が自然
- 変更時に利用側へ影響を与えることを許容できる
- Shared Kernelとして明確な責任を持てる

逆に、

> 「2つのFeatureで似たコードがある」

だけではShared Kernelへ移しません。

まずは各Featureに具体的な実装を置き、必要性が明確になってから共有化します。

---

## 8. Seedworkへ移す基準

Seedworkも同様に、必要以上に大きくしません。

次の条件を満たす場合に移動を検討します。

- 複数Featureで実際に利用される
- 特定Featureの業務知識に依存しない
- DDD / アプリケーション基盤として再利用できる
- 共通化によるメリットが明確

Feature固有の業務ルールをSeedworkへ移してはいけません。

---

## 9. AIがモジュールを生成するときの判断手順

AIが新しいFeatureやモジュールを生成する場合は、次の順序で判断します。

### Step 1. Feature境界を確認する

「何の業務機能か」を明確にします。

### Step 2. 最小構成を考える

最初から、

- domain
- application
- infrastructure
- presentation
- repository
- handler
- dto
- result
- unit of work

などをすべて作らないでください。

### Step 3. 必要な責務だけ配置する

そのFeatureで実際に必要なものだけを作ります。

### Step 4. 複雑になったら分割する

1ファイルや1モジュールが大きくなった場合に、Domain / Application / Infrastructureなどへ分割します。

### Step 5. 共有が必要になったら移動を検討する

実際に複数Featureで共有されるようになった時点で、`shared_kernel` や `seedwork` への移動を検討します。

### Step 6. 境界を確認する

最終的に、

- Domainの業務ルールが守られているか
- Feature間の不要な直接依存がないか
- ApplicationとInfrastructureの責務が混ざっていないか
- 不要な抽象化を追加していないか

を確認します。

---

## 10. 禁止する考え方

以下のような理由だけでモジュールを追加・分割してはいけません。

- 「DDDでは必須だから」
- 「VSAではこのフォルダ構成だから」
- 「Clean Architectureではこの層が必要だから」
- 「将来必要になるかもしれないから」
- 「AIがコードを生成しやすいから」
- 「ファイル数が多い方が設計らしく見えるから」

ルールの目的は、**コードを増やすことではなく、変更しやすく境界を守りやすい構造を作ること**です。

---

## 11. 最終原則

本プロジェクトのモジュール設計では、次の原則を優先します。

> **Featureを中心にコードを近くへ置く。**
>
> **必要なものだけ作る。**
>
> **複雑になったら分割する。**
>
> **実際に共有が必要になったら共通化する。**
>
> **境界は厳格に、構造は柔軟にする。**

つまり、

**「VSAだから固定構造にする」のではなく、「VSAを使って変更の影響範囲を小さくする」**

ことを目的とします。
