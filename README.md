## セットアップ

本プロジェクトは `src` レイアウトを採用しています。実行時に `ModuleNotFoundError` が発生する場合は、以下の設定を行ってください。

### 1. PYTHONPATH の設定
ターミナルから実行する場合、`src` ディレクトリをパスに含める必要があります。

```bash
# Linux / macOS
export PYTHONPATH=$PYTHONPATH:$(pwd)/src

# Windows (PowerShell)
$env:PYTHONPATH += ";$(pwd)\src"
