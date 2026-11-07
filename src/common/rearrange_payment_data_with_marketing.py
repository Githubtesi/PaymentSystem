"""決済入力データを台帳列順に並べ替え、集客集計からLINE名/BE-FE/L1-L2/LP名を照合して付加する。

配置例 (同じフォルダ内):
  CSV入力用 _ダミー(1).xlsx
  台帳_ダミー.xlsx
  data/【WLF】システム集客集計.xlsx

実行: pip install openpyxl && python rearrange_payment_data_with_marketing.py
出力: コピー用_台帳列順.xlsx (元ファイルは変更しません)
"""
from pathlib import Path
import re
from openpyxl import load_workbook, Workbook
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
    DATA_DIR / "excel" / "CSV入力用.xlsx",
    DATA_DIR / "CSV入力用.xlsx",
    DATA_DIR / "CSV入力用.xlsx",
])
LEDGER_FILE = find_file([
    DATA_DIR / "excel" / "【WLF】台帳.xlsx",
    DATA_DIR / "【WLF】台帳.xlsx",
])

MARKETING_FILE = find_file([
    DATA_DIR / "excel" / "【WLF】システム集客集計.xlsx",
    DATA_DIR / "【WLF】システム集客集計.xlsx",
])

OUTPUT_FILE = DATA_DIR / "excel" / "コピー用_台帳列順.xlsx"


SHEET_MAP = {
    "ロボペイall": "【着金】ロボペイ（カード）",
    "アクアゲイツall": "【着金】アクアゲイツ（過去データ）",
    "テレコムall": "【着金】テレコム",
}
HEADER_ALIASES = {
    "アクアゲイツall": {"住所（県）": "住所（都道府県）", "決済額": "金額"},
    "ロボペイall": {},
    "テレコムall": {},
}
LEDGER_HEADER_ROW = 2
INPUT_HEADER_ROW = 1
INPUT_DATA_START_ROW = 2

# 集客集計のシート名と、照合に使うLINE名列・分類・L1/L2
MARKETING_SHEETS = [
    ("L1ウェビナー申込Lステップ", "回答者名", "BE", "L1", 2, 3),
    ("L2ウェビナー申込Lステップ", "回答者名", "BE", "L2", 1, 2),
    ("L1_FEWeb申込着金L-step", "LINE登録名", "FE", "L1", 1, 2),
    ("L2_FEWeb申込着金L-step", "LINE登録名", "FE", "L2", 1, 2),
    ("電話申込着金", "LINE名", "", "", 2, 3),
    ("CS購入者情報", "LINE名", "", "", 1, 2),
]


def norm_header(v):
    return "" if v is None else str(v).strip()


def norm_text(v):
    if v is None:
        return ""
    s = str(v).strip().lower()
    s = re.sub(r"[\s　\-()（）＋+.]", "", s)
    return s


def norm_phone(v):
    if v is None:
        return ""
    # Excel numeric values may appear as float; retain digits only.
    digits = re.sub(r"\D", "", str(v))
    if digits.startswith("81") and len(digits) >= 11:
        digits = "0" + digits[2:]
    return digits


def row_header_positions(ws, header_row):
    result = {}
    for col in range(1, ws.max_column + 1):
        h = norm_header(ws.cell(header_row, col).value)
        if h and h not in result:
            result[h] = col
    return result


def choose_header(headers, candidates):
    for name in candidates:
        if name in headers:
            return headers[name]
    return None


def build_marketing_index(marketing_wb):
    """照合indexを作成。優先順位は電話番号→メール→氏名。
    1つのキーに複数の候補があれば先に登録されたシート/行を保持。
    """
    index = {"phone": {}, "email": {}, "name": {}}
    for sheet_name, line_header, category, level, header_row, data_start in MARKETING_SHEETS:
        if sheet_name not in marketing_wb.sheetnames:
            print(f"[集客照合スキップ] シートなし: {sheet_name}")
            continue
        ws = marketing_wb[sheet_name]
        headers = row_header_positions(ws, header_row)
        phone_col = choose_header(headers, ["電話番号", "TEL", "電話", "携帯電話", "電話番号（ハイフンなし）"])
        email_col = choose_header(headers, ["Eメール", "メールアドレス", "MAIL", "メール", "Email"])
        name_col = choose_header(headers, ["名前(日本語)", "本名", "氏名", "名前", "回答者名", "LINE登録名", "表示名"])
        line_col = headers.get(line_header)
        lp_col = headers.get("LP名")

        # CS購入者情報は、データ上に明確な列見出しがない形式のため列位置を指定。
        if sheet_name == "CS購入者情報":
            # 6列目=LINE名、7列目=本名、8列目=メールアドレス、10列目=電話番号
            line_col, name_col, email_col, phone_col = 6, 7, 8, 10
            # CS購入者情報のLP名は30列目
            lp_col = 30

        # 電話申込着金は TEL/MAIL の見出しが特殊、CS購入者情報は電話/メール列を併用。
        if sheet_name == "電話申込着金":
            phone_col = choose_header(headers, ["TEL", "電話番号"])
            email_col = choose_header(headers, ["MAIL", "メールアドレス", "Eメール"])
            name_col = headers.get("名前")
        elif sheet_name == "CS購入者情報":
            # 上で固定列を設定済み（このシートには列見出しがありません）。
            pass

        if line_col is None:
            print(f"[集客照合スキップ] LINE名列がありません: {sheet_name}/{line_header}")
            continue

        for row in range(data_start, ws.max_row + 1):
            line_name = ws.cell(row, line_col).value
            if line_name is None or not str(line_name).strip():
                continue
            lp_name = ws.cell(row, lp_col).value if lp_col else ""
            lp_name = "" if lp_name is None or norm_header(lp_name) == "LP名" else str(lp_name).strip()
            entry = {"line_name": str(line_name).strip(), "category": category, "level": level, "lp_name": lp_name, "sheet": sheet_name}
            keys = []
            if phone_col:
                phone = norm_phone(ws.cell(row, phone_col).value)
                if phone:
                    keys.append(("phone", phone))
            if email_col:
                email = norm_text(ws.cell(row, email_col).value)
                if email:
                    keys.append(("email", email))
            if name_col:
                name = norm_text(ws.cell(row, name_col).value)
                if name:
                    keys.append(("name", name))
            for kind, key in keys:
                index[kind].setdefault(key, entry)
    return index


def lookup_marketing(index, phone=None, email=None, name=None):
    keys = [("phone", norm_phone(phone)), ("email", norm_text(email)), ("name", norm_text(name))]
    for kind, key in keys:
        if key and key in index[kind]:
            return index[kind][key]
    return {"line_name": "", "category": "", "level": "", "lp_name": "", "sheet": ""}


def get_input_rows(ws):
    result = []
    for row_num in range(INPUT_DATA_START_ROW, ws.max_row + 1):
        values = [ws.cell(row_num, col).value for col in range(1, ws.max_column + 1)]
        if any(v is not None for v in values):
            result.append((row_num, values))
    return result


def build_output_sheet(output_wb, input_ws, ledger_ws, input_sheet_name, marketing_index=None):
    input_headers = row_header_positions(input_ws, INPUT_HEADER_ROW)
    aliases = HEADER_ALIASES.get(input_sheet_name, {})
    matched = []
    used_cols = set()
    for ledger_col in range(1, ledger_ws.max_column + 1):
        ledger_header = norm_header(ledger_ws.cell(LEDGER_HEADER_ROW, ledger_col).value)
        if not ledger_header:
            continue
        source_header = next((h for h in input_headers if aliases.get(h, h) == ledger_header), None)
        if source_header is None:
            continue
        input_col = input_headers[source_header]
        if input_col not in used_cols:
            matched.append((ledger_header, input_col))
            used_cols.add(input_col)

    if not matched:
        print(f"[警告] {input_sheet_name}: 対応列なし")
        return

    output_name = input_sheet_name.replace("all", "コピー用")[:31]
    out_ws = output_wb.create_sheet(output_name)
    style_header = Font(bold=True, color="FFFFFF")
    fill_header = PatternFill("solid", fgColor="4472C4")

    # 基本の台帳列を出力
    for out_col, (header, _) in enumerate(matched, start=1):
        c = out_ws.cell(1, out_col, header)
        c.font, c.fill = style_header, fill_header
        out_ws.column_dimensions[get_column_letter(out_col)].width = max(12, min(24, len(header) * 2 + 2))

    # ロボペイ用の追加列: 1空欄、BE/FE、5空欄、LINE名、L1/L2、LP名
    extra_cols = {}
    if input_sheet_name == "ロボペイall":
        start_col = len(matched) + 1
        extra_cols = {"BE/FE": start_col + 1, "LINE名": start_col + 7, "L1/L2": start_col + 8, "LP名": start_col + 9}
        for label, col in extra_cols.items():
            c = out_ws.cell(1, col, label)
            c.font, c.fill = style_header, fill_header
            out_ws.column_dimensions[get_column_letter(col)].width = max(14, len(label) * 2 + 2)

    data_rows = get_input_rows(input_ws)
    for out_row, (_, source_values) in enumerate(data_rows, start=2):
        for out_col, (_, input_col) in enumerate(matched, start=1):
            out_ws.cell(out_row, out_col, source_values[input_col - 1])

        if extra_cols and marketing_index:
            # 入力元の照合情報は電話番号・Eメール・名前(日本語)の順で利用
            source = {h: source_values[col - 1] for h, col in input_headers.items()}
            phone = source.get("電話番号") or source.get("TEL")
            email = source.get("Eメール") or source.get("メールアドレス") or source.get("MAIL")
            name = source.get("名前(日本語)") or source.get("名前") or source.get("姓")
            info = lookup_marketing(marketing_index, phone, email, name)
            out_ws.cell(out_row, extra_cols["BE/FE"], info["category"])
            out_ws.cell(out_row, extra_cols["LINE名"], info["line_name"])
            out_ws.cell(out_row, extra_cols["L1/L2"], info["level"])
            out_ws.cell(out_row, extra_cols["LP名"], info["lp_name"])

    out_ws.freeze_panes = "A2"
    out_ws.auto_filter.ref = out_ws.dimensions
    print(f"[完了] {input_sheet_name} -> {output_name}: {len(matched)}列 / {len(data_rows)}件")


def main():
    for path in (INPUT_FILE, LEDGER_FILE):
        if not path.exists():
            raise FileNotFoundError(f"Excelファイルが見つかりません: {path}")
    input_wb = load_workbook(INPUT_FILE, data_only=True)
    ledger_wb = load_workbook(LEDGER_FILE, data_only=True)
    marketing_index = None
    if MARKETING_FILE.exists():
        marketing_wb = load_workbook(MARKETING_FILE, data_only=True)
        marketing_index = build_marketing_index(marketing_wb)
        print("[集客照合] index作成完了")
    else:
        print(f"[警告] 集客集計ファイルが見つからないため、追加照合を行いません: {MARKETING_FILE}")

    output_wb = Workbook()
    output_wb.remove(output_wb.active)
    for input_sheet_name, ledger_sheet_name in SHEET_MAP.items():
        if input_sheet_name not in input_wb.sheetnames:
            print(f"[スキップ] 入力シートなし: {input_sheet_name}")
            continue
        if ledger_sheet_name not in ledger_wb.sheetnames:
            print(f"[スキップ] 台帳シートなし: {ledger_sheet_name}")
            continue
        build_output_sheet(output_wb, input_wb[input_sheet_name], ledger_wb[ledger_sheet_name], input_sheet_name, marketing_index)

    if not output_wb.sheetnames:
        raise RuntimeError("コピー用シートが作成されませんでした。シート名の対応を確認してください。")
    output_wb.save(OUTPUT_FILE)
    print(f"\n出力しました: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
