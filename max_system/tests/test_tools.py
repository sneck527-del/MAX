"""测试工具模块"""

import pytest


class TestTalkerTools:
    """Talker工具测试"""

    @pytest.mark.asyncio
    async def test_leadcatch_classify_high_intent(self):
        from max_system.tools.talker_tools import leadcatch_classify

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
        from max_system.tools.talker_tools import needanaly_report

        result = await needanaly_report({
            "client_name": "李先生",
            "family": "一家三口+老人",
            "spatial": "需要书房和充足的收纳空间",
            "aesthetic": "喜欢温暖简约风格",
            "pain_points": "采光不好，收纳不够",
        })
        assert result["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_talkscript_generate(self):
        from max_system.tools.talker_tools import talkscript_generate

        result = await talkscript_generate({
            "client_name": "王女士",
            "stage": "初次沟通",
            "client_type": "首次装修",
        })
        assert result["content"][0]["type"] == "text"
        data = result["content"][0]["text"]
        assert "话术" in data or "破冰" in data

    @pytest.mark.asyncio
    async def test_contractpro_draft(self):
        from max_system.tools.talker_tools import contractpro_draft

        result = await contractpro_draft({
            "client_name": "赵先生",
            "address": "XX小区12栋301",
            "area": "120",
            "total_price": "250000",
        })
        assert result["content"][0]["type"] == "text"
        data = result["content"][0]["text"]
        assert "草稿" in data

    @pytest.mark.asyncio
    async def test_datastat_report(self):
        from max_system.tools.talker_tools import datastat_report

        result = await datastat_report({"period": "本月"})
        assert result["content"][0]["type"] == "text"


class TestAfterProTools:
    """AfterPro工具测试"""

    @pytest.mark.asyncio
    async def test_returnvisit_schedule(self):
        from max_system.tools.afterpro_tools import returnvisit_schedule

        result = await returnvisit_schedule({
            "project_name": "XX别墅装修",
            "client_name": "陈先生",
            "visit_type": "竣工3个月回访",
        })
        assert result["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_issuefix_track(self):
        from max_system.tools.afterpro_tools import issuefix_track

        result = await issuefix_track({
            "project_name": "XX小区",
            "issue_desc": "卫生间墙面瓷砖空鼓",
            "severity": "重要",
        })
        assert result["content"][0]["type"] == "text"
        data = result["content"][0]["text"]
        assert "ISS-" in data


class TestMediaProTools:
    """MediaPro工具测试"""

    @pytest.mark.asyncio
    async def test_contentgen_draft(self):
        from max_system.tools.mediapro_tools import contentgen_draft

        result = await contentgen_draft({
            "platform": "小红书",
            "topic": "现代简约风装修",
            "style": "种草分享",
        })
        assert result["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_casepack_package(self):
        from max_system.tools.mediapro_tools import casepack_package

        result = await casepack_package({
            "project_name": "XX别墅",
            "style": "现代简约",
            "highlights": "LDK一体化设计",
        })
        assert result["content"][0]["type"] == "text"


class TestHelperTools:
    """Helper工具测试"""

    @pytest.mark.asyncio
    async def test_helper_batch_generate(self):
        from max_system.tools.helper_tools import helper_batch_generate

        result = await helper_batch_generate({
            "doc_type": "量房单",
            "projects": json.dumps([{
                "name": "XX别墅项目",
                "client": "张先生",
                "items": {"户型": "200㎡", "风格": "现代简约"},
            }]),
            "validate": True,
        })
        assert result["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_helper_feishu_alert(self):
        from max_system.tools.helper_tools import helper_feishu_sync_alert

        result = await helper_feishu_sync_alert({
            "alert_type": "reminder",
            "title": "客户跟进提醒",
            "content": "张先生已7天未跟进，请安排回访",
            "urgency": "normal",
        })
        assert result["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_helper_knowledge_catalog(self):
        from max_system.tools.helper_tools import helper_knowledge_catalog

        result = await helper_knowledge_catalog({"action": "catalog"})
        assert result["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_helper_obsidian_archive(self, tmp_path):
        from max_system.tools.helper_tools import helper_obsidian_full_archive

        # Temporarily redirect vault path
        import max_system.tools.helper_tools as ht
        original = ht._vault_path
        ht._vault_path = tmp_path

        try:
            result = await helper_obsidian_full_archive({
                "project_name": "测试项目",
                "category": "projects",
                "documents": json.dumps([{
                    "title": "测试文档",
                    "content": "这是测试内容",
                    "tags": ["测试"],
                }]),
            })
            assert result["content"][0]["type"] == "text"
        finally:
            ht._vault_path = original


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


import json
