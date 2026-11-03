"""
Excel決済データ読込クラス
対象シート: ロボペイall / アクアゲイツall / テレコムall
依存: pip install openpyxl
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


@dataclass
class PaymentRecord:
    """決済データ1行分を保持する基本クラス。"""
    source: str
    row_number: int
    data: dict[str, Any]

    def get(self, field_name: str, default: Any = None) -> Any:
        """列名を指定して値を取得する。"""
        return self.data.get(field_name, default)

    def to_dict(self) -> dict[str, Any]:
        """保持しているデータを辞書として返す。"""
        return self.data.copy()


class RoboPayRecord(PaymentRecord):
    """ロボペイの決済データ1行分。"""


class AquaGatesRecord(PaymentRecord):
    """アクアゲイツの決済データ1行分。"""


class TelecomRecord(PaymentRecord):
    """テレコムの決済データ1行分。"""


class ExcelPaymentReader:
    """Excelから各決済サービスのデータを読み込み、クラス構造で保持する。"""

    SHEET_RECORD_TYPES = {
        "ロボペイall": RoboPayRecord,
        "アクアゲイツall": AquaGatesRecord,
        "テレコムall": TelecomRecord,
    }

    def __init__(self, excel_path: str | Path):
        self.excel_path = Path(excel_path)
        self.robopay: list[RoboPayRecord] = []
        self.aqua_gates: list[AquaGatesRecord] = []
        self.telecom: list[TelecomRecord] = []

    def load(self) -> "ExcelPaymentReader":
        """Excelを読み込み、サービス別のレコードリストを設定する。"""
        if not self.excel_path.exists():
            raise FileNotFoundError(f"Excelファイルが見つかりません: {self.excel_path}")

        workbook = load_workbook(self.excel_path, data_only=True, read_only=True)
        try:
            for sheet_name, record_type in self.SHEET_RECORD_TYPES.items():
                if sheet_name not in workbook.sheetnames:
                    raise ValueError(f"必要なシートがありません: {sheet_name}")

                records = self._read_sheet(workbook[sheet_name], record_type)
                if record_type is RoboPayRecord:
                    self.robopay = records
                elif record_type is AquaGatesRecord:
                    self.aqua_gates = records
                elif record_type is TelecomRecord:
                    self.telecom = records
        finally:
            workbook.close()
        return self

    @staticmethod
    def _read_sheet(worksheet, record_type: type[PaymentRecord]) -> list[PaymentRecord]:
        """1行目をヘッダーとして読み込み、空行を除外する。"""
        rows = worksheet.iter_rows(values_only=True)
        headers = next(rows, None)
        if not headers:
            return []

        normalized_headers = [
            str(header).strip() if header is not None else ""
            for header in headers
        ]
        records = []
        for row_number, row in enumerate(rows, start=2):
            if all(value is None for value in row):
                continue

            data = {}
            for index, header in enumerate(normalized_headers):
                if not header:
                    continue
                data[header] = row[index] if index < len(row) else None

            records.append(record_type(
                source=worksheet.title,
                row_number=row_number,
                data=data,
            ))
        return records


if __name__ == "__main__":
    # プロジェクトのルートフォルダを取得
    BASE_DIR = Path(__file__).resolve().parents[2]

    # Excelファイルのパス
    # excel_path = BASE_DIR / "data" / "CSV入力用_ダミー.xlsx"
    excel_path = Path(r'C:\Users\tesiy\PycharmProjects\PaymentSystem\data\CSV入力用 _ダミー.xlsx')

    reader = ExcelPaymentReader(excel_path).load()

    print(f"ロボペイ件数: {len(reader.robopay)}")
    print(f"アクアゲイツ件数: {len(reader.aqua_gates)}")
    print(f"テレコム件数: {len(reader.telecom)}")

    if reader.robopay:
        record = reader.robopay[0]
        print("決済番号:", record.get("決済番号"))
        print("金額:", record.get("金額"))
        print("決済日時:", record.get("決済日時"))
