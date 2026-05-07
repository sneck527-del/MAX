"""Excel报价导入器测试"""

import json
import tempfile
from pathlib import Path

import pytest

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


# ============ helpers ============

def _make_xlsx(sheets: list[tuple[str, list[tuple]]]) -> Path:
    """用 openpyxl 创建一个临时 .xlsx 文件。返回文件路径。"""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets:
        ws = wb.create_sheet(title=name)
        for row in rows:
            ws.append(row)
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    wb.save(tmp.name)
    wb.close()
    return Path(tmp.name)


# ============ unit tests ============

class TestNormalizeHeader:
    def test_strips_whitespace(self):
        from max_system.integrations.quotes.excel_importer import _normalize_header
        assert _normalize_header("  名称  ") == "名称"

    def test_strips_newlines(self):
        from max_system.integrations.quotes.excel_importer import _normalize_header
        assert _normalize_header("材料\n名称") == "材料名称"


class TestMapColumns:
    def test_known_headers(self):
        from max_system.integrations.quotes.excel_importer import _map_columns
        mapping = _map_columns(["名称", "单价", "数量", "未知列"])
        assert mapping == {0: "name", 1: "unit_price", 2: "quantity"}

    def test_empty_headers(self):
        from max_system.integrations.quotes.excel_importer import _map_columns
        assert _map_columns([]) == {}

    def test_alias_variants(self):
        from max_system.integrations.quotes.excel_importer import _map_columns
        mapping = _map_columns(["项目名称", "报价单价", "规格型号"])
        assert mapping == {0: "name", 1: "unit_price", 2: "spec"}


class TestDetectType:
    def test_materials_with_subcategory(self):
        from max_system.integrations.quotes.excel_importer import _detect_type
        assert _detect_type(["类别", "子类", "名称", "单价"]) == "materials"

    def test_materials_with_brand(self):
        from max_system.integrations.quotes.excel_importer import _detect_type
        assert _detect_type(["分类", "名称", "品牌", "单价"]) == "materials"

    def test_construction_with_process_notes(self):
        from max_system.integrations.quotes.excel_importer import _detect_type
        assert _detect_type(["类别", "名称", "工艺说明", "单价"]) == "construction"

    def test_construction_plain(self):
        from max_system.integrations.quotes.excel_importer import _detect_type
        assert _detect_type(["名称", "单价", "数量"]) == "construction"


class TestCleanValue:
    def test_none_to_empty(self):
        from max_system.integrations.quotes.excel_importer import _clean_value
        assert _clean_value(None) == ""

    def test_float_is_int(self):
        from max_system.integrations.quotes.excel_importer import _clean_value
        assert _clean_value(3.0) == 3

    def test_float_rounded(self):
        from max_system.integrations.quotes.excel_importer import _clean_value
        assert _clean_value(3.456) == 3.46

    def test_string_stripped(self):
        from max_system.integrations.quotes.excel_importer import _clean_value
        assert _clean_value("  实木地板  ") == "实木地板"


class TestReverseField:
    def test_known_english_to_chinese(self):
        from max_system.integrations.quotes.excel_importer import _reverse_field
        assert _reverse_field("name") in ("名称", "项目名称", "材料名称", "产品名称", "施工项目")
        assert _reverse_field("unit_price") in ("单价", "报价单价", "综合单价", "报价", "价格")

    def test_unknown_returns_self(self):
        from max_system.integrations.quotes.excel_importer import _reverse_field
        assert _reverse_field("unknown_field") == "unknown_field"


class TestParseRowsToMaterials:
    def test_basic_grouping(self):
        from max_system.integrations.quotes.excel_importer import _parse_rows_to_materials
        rows = [
            {"category": "门窗", "subcategory": "入户门", "name": "防盗门", "unit_price": 3000},
            {"category": "门窗", "subcategory": "室内门", "name": "实木门", "unit_price": 2000},
            {"category": "地板", "subcategory": "实木地板", "name": "橡木地板", "unit_price": 350},
        ]
        result = _parse_rows_to_materials(rows)
        assert "门窗" in result
        assert "地板" in result
        assert "入户门" in result["门窗"]
        assert len(result["门窗"]["入户门"]) == 1
        assert result["门窗"]["入户门"][0]["名称"] == "防盗门"

    def test_default_category(self):
        from max_system.integrations.quotes.excel_importer import _parse_rows_to_materials
        rows = [{"name": "测试", "unit_price": 100}]
        result = _parse_rows_to_materials(rows)
        assert "其他材料" in result
        assert "通用" in result["其他材料"]


class TestParseRowsToConstruction:
    def test_basic_grouping(self):
        from max_system.integrations.quotes.excel_importer import _parse_rows_to_construction
        rows = [
            {"category": "拆除", "name": "拆墙", "unit_price": 50},
            {"category": "拆除", "name": "拆地砖", "unit_price": 30},
            {"category": "水电", "name": "布线", "unit_price": 80},
        ]
        result = _parse_rows_to_construction(rows)
        assert "拆除" in result
        assert "水电" in result
        assert len(result["拆除"]) == 2
        assert result["拆除"][0]["名称"] == "拆墙"

    def test_default_category(self):
        from max_system.integrations.quotes.excel_importer import _parse_rows_to_construction
        rows = [{"name": "测试", "unit_price": 100}]
        result = _parse_rows_to_construction(rows)
        assert "其他项目" in result


# ============ integration tests (use real openpyxl) ============

@pytest.mark.skipif(not HAS_OPENPYXL, reason="openpyxl not installed")
class TestParseExcel:
    def test_materials_excel(self):
        from max_system.integrations.quotes.excel_importer import parse_excel

        path = _make_xlsx([
            ("主材报价", [
                ("类别", "子类", "名称", "单位", "单价", "品牌"),
                ("门窗", "入户门", "防盗门", "樘", 3000, "盼盼"),
                ("门窗", "室内门", "实木门", "樘", 2000, "TATA"),
                ("地板", "实木地板", "橡木地板", "㎡", 350, "大自然"),
            ]),
        ])
        try:
            result = parse_excel(path)
            assert result["success"] is True
            assert result["type"] == "materials"
            assert result["rows_imported"] == 3
            assert result["sheets_processed"] == 1
            data = result["data"]
            assert "门窗" in data
            assert "地板" in data
            assert "入户门" in data["门窗"]
            assert len(data["门窗"]["入户门"]) == 1
        finally:
            path.unlink(missing_ok=True)

    def test_construction_excel(self):
        from max_system.integrations.quotes.excel_importer import parse_excel

        path = _make_xlsx([
            ("施工报价", [
                ("项目类别", "项目名称", "单位", "单价", "工艺说明"),
                ("拆除", "拆墙", "㎡", 50, "含垃圾清运"),
                ("拆除", "铲墙皮", "㎡", 15, "含基层处理"),
                ("水电", "布线", "m", 35, "含开槽"),
            ]),
        ])
        try:
            result = parse_excel(path)
            assert result["success"] is True
            assert result["type"] == "construction"
            assert result["rows_imported"] == 3
            data = result["data"]
            assert "拆除" in data
            assert "水电" in data
            assert len(data["拆除"]) == 2
        finally:
            path.unlink(missing_ok=True)

    def test_sheet_name_as_category(self):
        from max_system.integrations.quotes.excel_importer import parse_excel

        path = _make_xlsx([
            ("门窗", [
                ("名称", "单价", "单位"),
                ("防盗门", 3000, "樘"),
                ("实木门", 2000, "樘"),
            ]),
        ])
        try:
            result = parse_excel(path)
            assert result["success"] is True
            data = result["data"]
            assert "门窗" in data
        finally:
            path.unlink(missing_ok=True)

    def test_empty_sheets_skipped(self):
        from max_system.integrations.quotes.excel_importer import parse_excel

        path = _make_xlsx([
            ("空表", []),
            ("有效表", [
                ("类别", "名称", "单价"),
                ("拆除", "拆墙", 50),
            ]),
        ])
        try:
            result = parse_excel(path)
            assert result["success"] is True
            assert result["rows_imported"] == 1
            assert result["sheets_processed"] == 1
        finally:
            path.unlink(missing_ok=True)

    def test_no_data_returns_failure(self):
        from max_system.integrations.quotes.excel_importer import parse_excel

        path = _make_xlsx([
            ("Sheet1", [
                ("名称", "单价"),
            ]),
        ])
        try:
            result = parse_excel(path)
            assert result["success"] is False
            assert "未能" in result["message"]
        finally:
            path.unlink(missing_ok=True)

    def test_file_not_exists(self):
        from max_system.integrations.quotes.excel_importer import parse_excel
        result = parse_excel("/nonexistent/path/file.xlsx")
        assert result["success"] is False
        assert "不存在" in result["message"]

    def test_unsupported_extension(self):
        from max_system.integrations.quotes.excel_importer import parse_excel

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            f.write(b"test")
            csv_path = f.name
        try:
            result = parse_excel(csv_path)
            assert result["success"] is False
            assert ".csv" in result["message"]
        finally:
            Path(csv_path).unlink(missing_ok=True)

    def test_header_on_row_3(self):
        from max_system.integrations.quotes.excel_importer import parse_excel

        path = _make_xlsx([
            ("报价表", [
                ("装修报价单", None, None),
                ("日期：2025-01-01", None, None),
                ("类别", "名称", "单价"),
                ("拆除", "拆墙", 50),
            ]),
        ])
        try:
            result = parse_excel(path)
            assert result["success"] is True
            assert result["rows_imported"] == 1
        finally:
            path.unlink(missing_ok=True)


class TestSaveToWorkspace:
    def test_save_materials_new(self):
        from max_system.integrations.quotes.excel_importer import save_to_workspace

        with tempfile.TemporaryDirectory() as tmpdir:
            quotes_path = Path(tmpdir) / "quotes"
            data = {"门窗": {"入户门": [{"名称": "防盗门", "单价": 3000}]}}
            result = save_to_workspace(data, quotes_path, "materials")

            assert result["success"] is True
            saved = json.loads((quotes_path / "材料库.json").read_text(encoding="utf-8"))
            assert "门窗" in saved
            assert saved["门窗"]["入户门"][0]["名称"] == "防盗门"

    def test_save_construction_new(self):
        from max_system.integrations.quotes.excel_importer import save_to_workspace

        with tempfile.TemporaryDirectory() as tmpdir:
            quotes_path = Path(tmpdir) / "quotes"
            data = {"拆除": [{"名称": "拆墙", "单价": 50}]}
            result = save_to_workspace(data, quotes_path, "construction")

            assert result["success"] is True
            saved = json.loads((quotes_path / "施工库.json").read_text(encoding="utf-8"))
            assert "拆除" in saved
            assert saved["拆除"][0]["名称"] == "拆墙"

    def test_merge_with_existing(self):
        from max_system.integrations.quotes.excel_importer import save_to_workspace

        with tempfile.TemporaryDirectory() as tmpdir:
            quotes_path = Path(tmpdir) / "quotes"
            quotes_path.mkdir(parents=True)
            existing = {"门窗": {"入户门": [{"名称": "防盗门", "单价": 3000}]}}
            (quotes_path / "材料库.json").write_text(
                json.dumps(existing, ensure_ascii=False), encoding="utf-8"
            )

            new_data = {"门窗": {"入户门": [{"名称": "子母门", "单价": 4500}]}}
            result = save_to_workspace(new_data, quotes_path, "materials")

            assert result["success"] is True
            saved = json.loads((quotes_path / "材料库.json").read_text(encoding="utf-8"))
            items = saved["门窗"]["入户门"]
            names = [i["名称"] for i in items]
            assert "防盗门" in names
            assert "子母门" in names


class TestParseExcelMissingOpenpyxl:
    """当 openpyxl 未安装时 parse_excel 应返回友好错误"""

    def test_returns_friendly_error(self, monkeypatch):
        monkeypatch.setattr(
            "max_system.integrations.quotes.excel_importer.HAS_OPENPYXL", False
        )
        from max_system.integrations.quotes.excel_importer import parse_excel
        result = parse_excel("/tmp/test.xlsx")
        assert result["success"] is False
        assert "openpyxl" in result["message"]
