"""
CSV入力用Excelを台帳の列順に並べ替え、Ctrl+C / Ctrl+V用Excelを作成する。
配置: src/common/rearrange_payment_data.py
依存: pip install openpyxl
"""
from pathlib import Path
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

def find_file(candidates):
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        "対象Excelが見つかりません。確認したパス:\n"
        + "\n".join(str(path) for path in candidates)
    )

INPUT_FILE = find_file([
    DATA_DIR / "excel" / "CSV入力用_ダミー.xlsx",
    DATA_DIR / "CSV入力用_ダミー.xlsx",
    DATA_DIR / "CSV入力用 _ダミー.xlsx",
])
LEDGER_FILE = find_file([
    DATA_DIR / "excel" / "台帳_ダミー.xlsx",
    DATA_DIR / "台帳_ダミー.xlsx",
])
OUTPUT_FILE = DATA_DIR / "excel" / "コピー用_台帳列順.xlsx"

SHEET_MAP = {
    "ロボペイall": "【着金】ロボペイ（カード）",
    "アクアゲイツall": "【着金】アクアゲイツ（過去データ）",
    "テレコムall": "【着金】テレコム",
}
HEADER_ALIASES = {
    "アクアゲイツall": {
        "住所（県）": "住所（都道府県）",
        "決済額": "金額",
    },
}
INPUT_HEADER_ROW = 1
LEDGER_HEADER_ROW = 2
DATA_START_ROW = 2

def header(value):
    return str(value).strip() if value is not None else ""

def create_copy_sheet(output_wb, input_ws, ledger_ws, input_name):
    input_columns = {}
    for col in range(1, input_ws.max_column + 1):
        name = header(input_ws.cell(INPUT_HEADER_ROW, col).value)
        if name and name not in input_columns:
            input_columns[name] = col

    aliases = HEADER_ALIASES.get(input_name, {})
    matched_columns = []
    used_columns = set()

    # 台帳見出しの並びに合わせて、入力側にある列のみ抽出
    for ledger_col in range(1, ledger_ws.max_column + 1):
        ledger_name = header(ledger_ws.cell(LEDGER_HEADER_ROW, ledger_col).value)
        if not ledger_name:
            continue
        source_name = next(
            (name for name in input_columns if aliases.get(name, name) == ledger_name),
            None,
        )
        if source_name is None:
            continue
        source_col = input_columns[source_name]
        if source_col in used_columns:
            continue
        matched_columns.append((ledger_name, source_col))
        used_columns.add(source_col)

    if not matched_columns:
        print(f"[警告] {input_name}: 対応列がありません")
        return

    output_name = input_name.replace("all", "コピー用")[:31]
    output_ws = output_wb.create_sheet(output_name)

    for out_col, (name, _) in enumerate(matched_columns, start=1):
        cell = output_ws.cell(1, out_col, name)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4472C4")
        output_ws.column_dimensions[get_column_letter(out_col)].width = max(
            12, min(24, len(name) * 2 + 2)
        )

    count = 0
    for source_row in range(DATA_START_ROW, input_ws.max_row + 1):
        if all(input_ws.cell(source_row, col).value is None
               for col in range(1, input_ws.max_column + 1)):
            continue
        count += 1
        for out_col, (_, source_col) in enumerate(matched_columns, start=1):
            output_ws.cell(
                count + 1, out_col, input_ws.cell(source_row, source_col).value
            )

    output_ws.freeze_panes = "A2"
    output_ws.auto_filter.ref = output_ws.dimensions
    print(f"[完了] {input_name}: {len(matched_columns)}列 / {count}件")

def main():
    input_wb = load_workbook(INPUT_FILE, data_only=True, read_only=True)
    ledger_wb = load_workbook(LEDGER_FILE, data_only=True, read_only=True)
    output_wb = Workbook()
    output_wb.remove(output_wb.active)

    try:
        for input_name, ledger_name in SHEET_MAP.items():
            if input_name not in input_wb.sheetnames:
                print(f"[スキップ] 入力シートがありません: {input_name}")
                continue
            if ledger_name not in ledger_wb.sheetnames:
                print(f"[スキップ] 台帳シートがありません: {ledger_name}")
                continue
            create_copy_sheet(
                output_wb, input_wb[input_name], ledger_wb[ledger_name], input_name
            )
    finally:
        input_wb.close()
        ledger_wb.close()

    if not output_wb.sheetnames:
        raise RuntimeError("出力シートが作成されませんでした。シート名・見出しを確認してください。")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output_wb.save(OUTPUT_FILE)
    print(f"\n出力ファイル: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
