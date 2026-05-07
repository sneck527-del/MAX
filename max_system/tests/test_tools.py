"""测试工具模块"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestSalesTools:
    """销售工具测试"""

    @pytest.mark.asyncio
    async def test_leadcatch_classify(self):
        from max_system.tools.sales_tools import leadcatch_classify

        result = await leadcatch_classify({
            "name": "张先生",
            "budget": "60-80万",
            "unit_type": "200㎡别墅",
            "stage": "已交房",
            "source": "朋友推荐",
            "core_needs": "需要充足收纳空间，风格偏好现代简约",
        })
        assert result["content"][0]["type"] == "text"
        data = result["content"][0]["text"]
        assert "高" in data or "score" in data

    @pytest.mark.asyncio
    async def test_needanaly_report(self):
        from max_system.tools.sales_tools import needanaly_report

        result = await needanaly_report({
            "client_name": "李先生",
        })
        assert result["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_datastat_report(self):
        from max_system.tools.sales_tools import datastat_report

        result = await datastat_report({"period": "本月"})
        assert result["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_datastat_report_month_filtering(self):
        """测试 datastat_report 按"本月"过滤时仅统计本月创建的客户。"""
        from max_system.tools.sales_tools import datastat_report
        from max_system.tools.clientmgr_tools import _clients_db

        # 保存原始数据
        original_clients = dict(_clients_db)

        try:
            _clients_db.clear()
            now = datetime.now()

            # 本月创建的客户
            _clients_db["C_TEST_001"] = {
                "client_id": "C_TEST_001",
                "name": "本月客户",
                "intent": "高",
                "status": "跟进中",
                "created_at": now.replace(day=15).isoformat(),
            }
            # 上月创建的客户
            last_month = now.replace(day=1) - timedelta(days=1)
            _clients_db["C_TEST_002"] = {
                "client_id": "C_TEST_002",
                "name": "上月客户",
                "intent": "中",
                "status": "新建",
                "created_at": last_month.replace(day=10).isoformat(),
            }

            result = await datastat_report({"period": "本月"})
            data = json.loads(result["content"][0]["text"])
            assert data["总量统计"]["总线索数"] == 1
            assert data["总量统计"]["高意向"] == 1
            assert data["总量统计"]["中意向"] == 0
        finally:
            _clients_db.clear()
            _clients_db.update(original_clients)


class TestServiceTools:
    """售后工具测试"""

    @pytest.mark.asyncio
    async def test_returnvisit_schedule(self):
        from max_system.tools.service_tools import returnvisit_schedule

        result = await returnvisit_schedule({
            "project_name": "XX别墅装修",
            "client_name": "陈先生",
            "visit_type": "竣工3个月回访",
        })
        assert result["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_issuefix_track(self):
        from max_system.tools.service_tools import issuefix_track

        result = await issuefix_track({
            "project_name": "XX小区",
            "issue_desc": "卫生间墙面瓷砖空鼓",
            "severity": "重要",
        })
        assert result["content"][0]["type"] == "text"
        data = result["content"][0]["text"]
        assert "ISS-" in data


class TestMarketingTools:
    """营销工具测试"""

    @pytest.mark.asyncio
    async def test_leadtransfer_qualify(self):
        from max_system.tools.marketing_tools import leadtransfer_qualify

        result = await leadtransfer_qualify({
            "lead_content": "我想装修120平米的房子，预算50万左右",
            "lead_source": "小红书私信",
            "platform": "小红书",
        })
        assert result["content"][0]["type"] == "text"
        data = json.loads(result["content"][0]["text"])
        assert "created_at" in data, "leadtransfer_qualify 应包含 created_at 字段"
        # 验证 created_at 是合法的ISO格式
        datetime.fromisoformat(data["created_at"])

    @pytest.mark.asyncio
    async def test_datareview_analyze(self):
        from max_system.tools.marketing_tools import datareview_analyze

        result = await datareview_analyze({"period": "本月"})
        assert result["content"][0]["type"] == "text"


class TestClientMgrTools:
    """客户管理工具测试"""

    @pytest.mark.asyncio
    async def test_create_and_query_client(self):
        from max_system.tools.clientmgr_tools import clientmgr_create_client, clientmgr_query_clients

        await clientmgr_create_client({
            "name": "测试客户",
            "phone": "13800138000",
            "city": "上海",
            "unit_type": "150㎡大平层",
        })

        results = await clientmgr_query_clients({"name": "测试客户"})
        assert results["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_client_tag_and_report(self):
        from max_system.tools.clientmgr_tools import client_tag_and_report

        result = await client_tag_and_report({"action": "report"})
        assert result["content"][0]["type"] == "text"


class TestProfileTools:
    """Profile工具测试"""

    @pytest.mark.asyncio
    async def test_profile_get_and_update(self):
        from max_system.tools.profile_tools import profile_get, profile_update
        result = await profile_get({"key": "company_name"})
        assert result["content"][0]["type"] == "text"


class TestScheduleTools:
    """定时任务工具测试"""

    @pytest.mark.asyncio
    async def test_schedule_list(self):
        from max_system.tools.schedule_tools import schedule_list
        result = await schedule_list({})
        assert result["content"][0]["type"] == "text"


class TestDocumentTools:
    """文档生成工具测试"""

    @pytest.mark.asyncio
    async def test_generate_document_list_templates(self):
        """测试列出模板目录"""
        from max_system.tools.document_tools import generate_document
        result = await generate_document({"template_name": "list"})
        assert result["content"][0]["type"] == "text"
        text = result["content"][0]["text"]
        assert "可用文档模板" in text
        # 应包含多个阶段
        assert "前期对接" in text or "设计方案" in text or "预算报价" in text

    @pytest.mark.asyncio
    async def test_generate_document_missing_template(self):
        """测试模板不存在"""
        from max_system.tools.document_tools import generate_document
        result = await generate_document({"template_name": "不存在的模板名称XYZ"})
        text = result["content"][0]["text"]
        assert "未找到模板" in text

    @pytest.mark.asyncio
    async def test_generate_document_without_template_name(self):
        """测试未指定 template_name"""
        from max_system.tools.document_tools import generate_document
        result = await generate_document({})
        text = result["content"][0]["text"]
        assert "请指定" in text or "template_name" in text or "list" in text

    @pytest.mark.asyncio
    async def test_generate_document_with_client_data(self):
        """测试用客户数据填充模板"""
        from max_system.tools.clientmgr_tools import clientmgr_create_client
        from max_system.tools.document_tools import generate_document

        # 先创建一个测试客户
        await clientmgr_create_client({
            "name": "张先生",
            "phone": "13900139000",
            "city": "北京朝阳区XX小区",
            "unit_type": "120㎡大平层",
            "budget": "50万",
            "design_fee": "5万",
        })

        # 生成文档 - 使用客户信息与装修需求登记表
        result = await generate_document({
            "template_name": "客户信息与装修需求登记表",
            "client_name": "张先生",
        })
        text = result["content"][0]["text"]
        # 应填充了客户数据或保留了模板结构
        assert "张先生" in text or "客户信息" in text or "需求" in text
        # 应有AI生成提示
        assert "AI生成" in text or "审核确认" in text

    @pytest.mark.asyncio
    async def test_generate_document_with_custom_data(self):
        """测试自定义变量填充"""
        from max_system.tools.document_tools import generate_document

        result = await generate_document({
            "template_name": "客户沟通纪要模板",
            "client_name": "测试客户",
            "custom_data": {"装修预算": "60万", "风格偏好": "现代简约"},
        })
        text = result["content"][0]["text"]
        # 至少返回了内容，且有AI草稿提示
        assert "AI生成" in text or "审核确认" in text

    @pytest.mark.asyncio
    async def test_generate_quote_document(self):
        """测试生成报价文档"""
        from max_system.tools.document_tools import generate_quote_document

        items = [
            {"name": "拆除旧门窗", "type": "engineering", "quantity": 1, "unit_price": 2000},
            {"name": "瓷砖铺贴", "type": "engineering", "quantity": 80, "unit_price": 65},
            {"name": "实木地板", "type": "material", "quantity": 50, "unit_price": 300},
        ]
        result = await generate_quote_document({
            "items": items,
            "client_name": "李先生",
            "project_name": "上海浦东XX花园",
        })
        text = result["content"][0]["text"]
        assert "装修工程报价单" in text
        assert "李先生" in text
        assert "拆除旧门窗" in text
        assert "瓷砖铺贴" in text
        assert "实木地板" in text
        assert "直接费用合计" in text
        assert "报价总计" in text
        assert "管理费" in text
        assert "税金" in text

    @pytest.mark.asyncio
    async def test_generate_quote_document_empty_items(self):
        """测试空报价项目"""
        from max_system.tools.document_tools import generate_quote_document

        result = await generate_quote_document({"items": []})
        text = result["content"][0]["text"]
        assert "请提供" in text


class TestProjectTools:
    """项目总览工具测试"""

    @pytest.mark.asyncio
    async def test_project_overview_no_client(self):
        """测试无匹配客户"""
        from max_system.tools.project_tools import project_overview

        result = await project_overview({"client_name": "不存在的客户ABC123"})
        text = result["content"][0]["text"]
        assert "未找到" in text

    @pytest.mark.asyncio
    async def test_project_overview_with_client(self):
        """测试有客户数据时的项目总览"""
        from max_system.tools.clientmgr_tools import clientmgr_create_client
        from max_system.tools.project_tools import project_overview

        # 创建测试客户
        await clientmgr_create_client({
            "name": "王女士",
            "phone": "13800001111",
            "city": "广州天河区XX花园",
            "unit_type": "200㎡别墅",
            "budget": "100万",
            "design_fee": "12万",
            "status": "施工中",
            "intent": "已签约",
            "follower": "李设计师",
        })

        result = await project_overview({"client_name": "王女士"})
        text = result["content"][0]["text"]
        assert "项目全景视图" in text
        assert "王女士" in text
        assert "客户信息" in text
        assert "广州天河" in text

    @pytest.mark.asyncio
    async def test_project_overview_with_client_id(self):
        """测试用客户编号查询"""
        from max_system.tools.clientmgr_tools import clientmgr_create_client, clientmgr_query_clients
        from max_system.tools.project_tools import project_overview

        # 创建客户并获取其 ID
        await clientmgr_create_client({
            "name": "赵先生",
            "phone": "13700002222",
            "city": "深圳南山区XX小区",
            "unit_type": "90㎡三居室",
        })

        # 查询获取 client_id
        query_result = await clientmgr_query_clients({"name": "赵先生"})
        import json
        clients = json.loads(query_result["content"][0]["text"])
        assert len(clients) > 0
        client_id = clients[0]["client_id"]

        result = await project_overview({"client_id": client_id})
        text = result["content"][0]["text"]
        assert "项目全景视图" in text
        assert "赵先生" in text

    @pytest.mark.asyncio
    async def test_project_overview_without_params(self):
        """测试不传任何参数"""
        from max_system.tools.project_tools import project_overview

        result = await project_overview({})
        text = result["content"][0]["text"]
        # 应该返回"未找到"信息
        assert "未找到" in text


class TestQuoteCalculation:
    """报价汇总计算测试"""

    @pytest.mark.asyncio
    async def test_calculate_summary_basic(self):
        from max_system.tools.quote_tools import quote_calculate_summary
        items = [
            {"name": "拆除旧门窗", "type": "engineering", "quantity": 1, "unit_price": 2000},
            {"name": "瓷砖铺贴", "type": "engineering", "quantity": 80, "unit_price": 65},
            {"name": "实木地板", "type": "material", "quantity": 50, "unit_price": 300},
        ]
        # 工程: 2000 + 5200 = 7200  |  产品: 15000  |  直接费: 22200
        # 管理费 8%: 1776  |  税 3.41%: 757.02  |  垃圾 800  |  保护 500  |  总计: 26033.02
        result = await quote_calculate_summary({"items": items})
        text = result["content"][0]["text"]
        import json
        data = json.loads(text)
        assert data["工程小计"] == 7200
        assert data["产品小计"] == 15000
        assert data["直接费用合计"] == 22200
        assert data["管理费"] == 1776.0
        assert data["税金"] == 757.02
        assert data["垃圾清运费"] == 800
        assert data["成品保护费"] == 500
        assert data["报价总计"] == 26033.02
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_calculate_summary_empty_items(self):
        from max_system.tools.quote_tools import quote_calculate_summary
        result = await quote_calculate_summary({"items": []})
        text = result["content"][0]["text"]
        assert "请提供" in text

    @pytest.mark.asyncio
    async def test_calculate_summary_string_items(self):
        from max_system.tools.quote_tools import quote_calculate_summary
        import json
        items_str = json.dumps([
            {"name": "墙面乳胶漆", "type": "engineering", "quantity": 100, "unit_price": 25},
        ])
        result = await quote_calculate_summary({"items": items_str})
        data = json.loads(result["content"][0]["text"])
        assert data["直接费用合计"] == 2500

    @pytest.mark.asyncio
    async def test_calculate_summary_zero_quantity(self):
        from max_system.tools.quote_tools import quote_calculate_summary
        items = [
            {"name": "某项目", "type": "engineering", "quantity": 0, "unit_price": 100},
        ]
        result = await quote_calculate_summary({"items": items})
        import json
        data = json.loads(result["content"][0]["text"])
        assert data["报价总计"] == data["垃圾清运费"] + data["成品保护费"]


class TestQuoteCacheIsolation:
    """报价缓存多工作区隔离测试"""

    def test_cache_reloads_on_workspace_switch(self):
        import sys
        # 清除模块级缓存
        for key in ("max_system.tools.quote_tools",):
            if key in sys.modules:
                del sys.modules[key]

        from max_system.tools import quote_tools

        with tempfile.TemporaryDirectory() as tmpdir:
            quotes_a = Path(tmpdir) / "ws_a" / "quotes"
            quotes_b = Path(tmpdir) / "ws_b" / "quotes"
            quotes_a.mkdir(parents=True)
            quotes_b.mkdir(parents=True)

            # 工作区A：门窗数据
            data_a = {"门窗": {"入户门": [{"名称": "防盗门", "单价": 3000}]}}
            (quotes_a / "材料库.json").write_text(json.dumps(data_a, ensure_ascii=False), encoding="utf-8")
            (quotes_a / "施工库.json").write_text("{}", encoding="utf-8")

            # 工作区B：地板数据
            data_b = {"地板": {"实木地板": [{"名称": "橡木地板", "单价": 350}]}}
            (quotes_b / "材料库.json").write_text(json.dumps(data_b, ensure_ascii=False), encoding="utf-8")
            (quotes_b / "施工库.json").write_text("{}", encoding="utf-8")

            # 用路径补丁模拟 workspace context
            class FakeWorkspace:
                def __init__(self, p):
                    self.quotes_path = p

            # 加载A
            quote_tools._loaded_path = None
            quote_tools._materials_db = None
            quote_tools._construction_db = None
            with patch.object(quote_tools, "_get_active_quotes_path", return_value=quotes_a):
                quote_tools._ensure_loaded()
                assert "门窗" in quote_tools._materials_db
                assert "地板" not in quote_tools._materials_db
                path_a = quote_tools._loaded_path

            # 切换到B
            with patch.object(quote_tools, "_get_active_quotes_path", return_value=quotes_b):
                quote_tools._ensure_loaded()
                assert "地板" in quote_tools._materials_db
                assert "门窗" not in quote_tools._materials_db
                path_b = quote_tools._loaded_path

            assert path_a != path_b

    def test_seed_defaults_copies_from_global(self):
        import sys
        for key in ("max_system.tools.quote_tools",):
            if key in sys.modules:
                del sys.modules[key]

        from max_system.tools import quote_tools

        with tempfile.TemporaryDirectory() as tmpdir:
            # 全局默认数据
            global_dir = Path(tmpdir) / "global_quotes"
            global_dir.mkdir(parents=True)
            default_data = {"门窗": {"入户门": [{"名称": "默认防盗门", "单价": 2500}]}}
            (global_dir / "材料库.json").write_text(json.dumps(default_data, ensure_ascii=False), encoding="utf-8")
            (global_dir / "施工库.json").write_text("{}", encoding="utf-8")

            # 空白工作区
            ws_dir = Path(tmpdir) / "ws_new" / "quotes"
            quote_tools._quote_path = global_dir
            quote_tools._seed_defaults(ws_dir)

            assert (ws_dir / "材料库.json").exists()
            assert (ws_dir / "施工库.json").exists()
            saved = json.loads((ws_dir / "材料库.json").read_text(encoding="utf-8"))
            assert "门窗" in saved


class TestQuoteImportIntegration:
    """报价导入集成测试"""

    @pytest.mark.asyncio
    async def test_import_clears_cache(self):
        import sys
        for key in ("max_system.tools.quote_tools",):
            if key in sys.modules:
                del sys.modules[key]

        from max_system.tools import quote_tools

        with tempfile.TemporaryDirectory() as tmpdir:
            quotes_path = Path(tmpdir) / "quotes"
            quotes_path.mkdir(parents=True)

            # 预加载旧缓存
            old_data = {"旧类别": {"旧子类": [{"名称": "旧项目", "单价": 100}]}}
            (quotes_path / "材料库.json").write_text(json.dumps(old_data, ensure_ascii=False), encoding="utf-8")
            (quotes_path / "施工库.json").write_text("{}", encoding="utf-8")

            quote_tools._loaded_path = None
            quote_tools._materials_db = None
            with patch.object(quote_tools, "_get_active_quotes_path", return_value=quotes_path):
                quote_tools._ensure_loaded()
                assert quote_tools._materials_db is not None
                assert "旧类别" in quote_tools._materials_db

            # 模拟导入清除缓存
            quote_tools._loaded_path = None
            quote_tools._materials_db = None

            # 写入新数据
            new_data = {"新类别": {"新子类": [{"名称": "新项目", "单价": 200}]}}
            (quotes_path / "材料库.json").write_text(json.dumps(new_data, ensure_ascii=False), encoding="utf-8")

            # 重新加载
            with patch.object(quote_tools, "_get_active_quotes_path", return_value=quotes_path):
                quote_tools._ensure_loaded()
                assert "新类别" in quote_tools._materials_db
                assert "旧类别" not in quote_tools._materials_db


class TestKnowledgeTools:
    """知识库工具测试"""

    @pytest.mark.asyncio
    async def test_knowledge_import_with_text_source(self):
        """测试通过text源批量导入知识文档。"""
        from max_system.tools.knowledge_tools import register_tools, knowledge_import
        from max_system.config.settings import MaxSettings

        with tempfile.TemporaryDirectory() as tmpdir:
            kb_path = Path(tmpdir) / "knowledge"
            kb_path.mkdir(exist_ok=True)

            # 创建mock settings
            settings = MaxSettings()
            settings.knowledge_base_path = kb_path

            # 注册以设置 _kb_path
            register_tools(settings)

            documents = [
                {"title": "公司设计标准", "content": "所有设计必须遵循国家标准...", "tags": "标准,设计", "category": "company_standards"},
                {"title": "现代简约案例", "content": "本案位于上海浦东，面积120平...", "tags": "案例,现代简约", "category": "case_database"},
            ]

            result = await knowledge_import({
                "source": "text",
                "documents": documents,
            })

            data = json.loads(result["content"][0]["text"])
            assert data["导入数量"] == 2
            assert len(data["导入文件"]) == 2
            assert data["错误"] == []
            assert data["success"] is True

            # 验证文件确实被创建
            for doc in documents:
                cat = doc.get("category", "company_standards")
                safe_name = "".join(c for c in doc["title"] if c.isalnum() or c in " _-")[:60]
                filepath = kb_path / cat / f"{safe_name}.md"
                assert filepath.exists(), f"文件应已创建: {filepath}"
                content = filepath.read_text(encoding="utf-8")
                assert doc["content"] in content

    @pytest.mark.asyncio
    async def test_knowledge_import_empty_documents(self):
        """测试空文档列表的text导入。"""
        from max_system.tools.knowledge_tools import register_tools, knowledge_import
        from max_system.config.settings import MaxSettings

        with tempfile.TemporaryDirectory() as tmpdir:
            kb_path = Path(tmpdir) / "knowledge"
            kb_path.mkdir(exist_ok=True)

            settings = MaxSettings()
            settings.knowledge_base_path = kb_path
            register_tools(settings)

            result = await knowledge_import({
                "source": "text",
                "documents": [],
            })

            text = result["content"][0]["text"]
            # 空文档应返回文本提示，不是 JSON
            assert "文本导入" in text or "参数" in text or "documents" in text or text.strip() == ""
            # 不应该报 JSON 解析错误

    @pytest.mark.asyncio
    async def test_knowledge_search_with_semantic_type(self):
        """测试语义搜索类型——在VectorStore不可用时应回退到关键词搜索。"""
        from max_system.tools.knowledge_tools import register_tools, knowledge_search
        from max_system.config.settings import MaxSettings

        with tempfile.TemporaryDirectory() as tmpdir:
            kb_path = Path(tmpdir) / "knowledge"
            kb_path.mkdir(exist_ok=True)

            # 创建一个测试知识文件
            cat_dir = kb_path / "company_standards"
            cat_dir.mkdir(parents=True, exist_ok=True)
            test_file = cat_dir / "测试标准.md"
            test_file.write_text("# 测试标准\n\n本文件包含室内设计的标准规范。\n\n施工要求严格按国家标准执行。", encoding="utf-8")

            settings = MaxSettings()
            settings.knowledge_base_path = kb_path
            register_tools(settings)

            # 使用semantic搜索类型——VectorStore可能不可用，应回退到keyword
            result = await knowledge_search({
                "query": "室内设计",
                "search_type": "semantic",
                "top_k": 5,
            })

            data = json.loads(result["content"][0]["text"])
            assert isinstance(data, list)
            # 无论语义还是关键词，都应该能找到结果
            assert len(data) > 0, "应返回搜索结果"
            # 验证返回的数据结构
            for item in data:
                assert "file" in item or "snippet" in item or "content" in item

    @pytest.mark.asyncio
    async def test_knowledge_search_hybrid_type(self):
        """测试混合搜索类型——关键词和语义结果合并去重。"""
        from max_system.tools.knowledge_tools import register_tools, knowledge_search
        from max_system.config.settings import MaxSettings

        with tempfile.TemporaryDirectory() as tmpdir:
            kb_path = Path(tmpdir) / "knowledge"
            kb_path.mkdir(exist_ok=True)

            cat_dir = kb_path / "company_standards"
            cat_dir.mkdir(parents=True, exist_ok=True)
            test_file = cat_dir / "设计规范2024.md"
            test_file.write_text("# 设计规范2024\n\n现代简约风格设计规范...\n\n国标参考: GB50327", encoding="utf-8")

            settings = MaxSettings()
            settings.knowledge_base_path = kb_path
            register_tools(settings)

            # hybrid模式：即使语义搜索不可用，也应回退到keyword
            result = await knowledge_search({
                "query": "设计规范",
                "search_type": "hybrid",
                "top_k": 3,
            })

            data = json.loads(result["content"][0]["text"])
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_knowledge_import_invalid_source(self):
        """测试无效的导入来源。"""
        from max_system.tools.knowledge_tools import register_tools, knowledge_import
        from max_system.config.settings import MaxSettings

        with tempfile.TemporaryDirectory() as tmpdir:
            kb_path = Path(tmpdir) / "knowledge"
            kb_path.mkdir(exist_ok=True)

            settings = MaxSettings()
            settings.knowledge_base_path = kb_path
            register_tools(settings)

            result = await knowledge_import({
                "source": "invalid_source",
            })

            text = result["content"][0]["text"]
            assert "不支持" in text

    @pytest.mark.asyncio
    async def test_knowledge_search_with_mock_vector_store(self):
        """测试语义搜索——mock VectorStore返回结果。"""
        from max_system.tools.knowledge_tools import (
            register_tools,
            knowledge_search,
            _get_vector_store,
            _vector_store,
        )
        from max_system.config.settings import MaxSettings

        # 创建mock VectorStore
        mock_vs = MagicMock()
        mock_vs.search.return_value = [
            {
                "id": "doc_001",
                "content": "现代简约风格设计标准，适用于大平层和别墅...",
                "metadata": {"category": "company_standards", "title": "设计标准"},
                "distance": 0.12,
            },
            {
                "id": "doc_002",
                "content": "欧式风格案例分享...",
                "metadata": {"category": "case_database", "title": "欧式案例"},
                "distance": 0.45,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            kb_path = Path(tmpdir) / "knowledge"
            kb_path.mkdir(exist_ok=True)

            settings = MaxSettings()
            settings.knowledge_base_path = kb_path
            register_tools(settings)

            # 替换全局_vector_store为mock
            original_vs = _vector_store
            try:
                # 直接替换模块级别的 _vector_store
                import max_system.tools.knowledge_tools as kt
                kt._vector_store = mock_vs

                result = await knowledge_search({
                    "query": "设计风格",
                    "search_type": "semantic",
                    "top_k": 2,
                })

                data = json.loads(result["content"][0]["text"])
                assert isinstance(data, list)
                assert len(data) == 2
                # 验证语义搜索结果中包含score
                assert data[0].get("source") == "semantic"
                assert data[1].get("source") == "semantic"
                # mock的VectorStore.search应该被调用
                mock_vs.search.assert_called_once()
            finally:
                kt._vector_store = original_vs

    @pytest.mark.asyncio
    async def test_datareview_analyze_empty_content_note(self):
        """测试datareview_analyze在内容库为空时显示提示。"""
        from max_system.tools.marketing_tools import datareview_analyze, _content_db

        # 保存原始数据
        original_content = list(_content_db)

        try:
            _content_db.clear()

            result = await datareview_analyze({"period": "本月"})
            data = json.loads(result["content"][0]["text"])
            assert data["内容产出"]["总发布量"] == 0
            assert "提示" in data
            assert "暂无内容发布数据" in data["提示"]
        finally:
            _content_db.clear()
            _content_db.extend(original_content)
