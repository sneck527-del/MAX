"""测试工具模块"""

import json
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
