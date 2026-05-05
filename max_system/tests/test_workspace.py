"""测试Workspace多租户隔离"""

import pytest
from pathlib import Path


class TestWorkspaceManager:
    """WorkspaceManager 创建和管理测试"""

    @pytest.fixture
    async def ws_manager(self, tmp_path):
        from max_system.config.workspace import WorkspaceManager
        base_dir = tmp_path / "workspaces"
        wm = WorkspaceManager(base_dir)
        await wm.initialize()
        yield wm
        await wm.close()

    async def test_create_workspace(self, ws_manager):
        """验证创建workspace时DB被正确创建"""
        ws = await ws_manager.get_workspace("chat_abc123")
        assert ws.workspace_id == "chat_abc123"
        assert ws.db_path.exists()
        assert ws.profile is not None

        # Verify the DB has the designer_profile table
        assert await ws.profile.is_empty()

    async def test_workspace_caching(self, ws_manager):
        """同一workspace_id返回相同的实例"""
        ws1 = await ws_manager.get_workspace("chat_same")
        ws2 = await ws_manager.get_workspace("chat_same")
        assert ws1 is ws2

    async def test_different_workspaces(self, ws_manager):
        """不同workspace_id返回不同的实例"""
        ws_a = await ws_manager.get_workspace("chat_aaa")
        ws_b = await ws_manager.get_workspace("chat_bbb")
        assert ws_a is not ws_b
        assert ws_a.db_path != ws_b.db_path


class TestWorkspaceProfileIsolation:
    """Workspace Profile隔离测试"""

    @pytest.fixture
    async def two_workspaces(self, tmp_path):
        from max_system.config.workspace import WorkspaceManager
        base_dir = tmp_path / "workspaces"
        wm = WorkspaceManager(base_dir)
        await wm.initialize()
        ws_a = await wm.get_workspace("company_a")
        ws_b = await wm.get_workspace("company_b")
        yield wm, ws_a, ws_b
        await wm.close()

    async def test_profile_independence(self, two_workspaces):
        """更新workspace A的profile不影响workspace B"""
        wm, ws_a, ws_b = two_workspaces

        # Set profile in workspace A
        await ws_a.profile.set("company_name", "梦想改造家")
        await ws_a.profile.set("design_style", "极简")
        await ws_a.profile.set("city", "上海")

        # Set profile in workspace B
        await ws_b.profile.set("company_name", "温馨小窝设计")
        await ws_b.profile.set("design_style", "日式")
        await ws_b.profile.set("city", "杭州")

        # Verify workspace A
        all_a = await ws_a.profile.get_all()
        assert all_a["company_name"] == "梦想改造家"
        assert all_a["design_style"] == "极简"
        assert all_a["city"] == "上海"

        # Verify workspace B
        all_b = await ws_b.profile.get_all()
        assert all_b["company_name"] == "温馨小窝设计"
        assert all_b["design_style"] == "日式"
        assert all_b["city"] == "杭州"

    async def test_profile_reset_isolation(self, two_workspaces):
        """重置workspace A的profile不影响workspace B"""
        wm, ws_a, ws_b = two_workspaces

        await ws_a.profile.set("company_name", "公司A")
        await ws_b.profile.set("company_name", "公司B")

        # Reset workspace A only
        await ws_a.profile.reset()

        # A should be empty, B should still have data
        assert await ws_a.profile.is_empty()
        assert await ws_b.profile.get("company_name") == "公司B"

    async def test_workspace_initial_state(self, two_workspaces):
        """每个workspace的初始状态应该是独立的空DB"""
        wm, ws_a, ws_b = two_workspaces

        assert await ws_a.profile.is_empty()
        assert await ws_b.profile.is_empty()

        # Both should have default fee rates
        all_a = await ws_a.profile.get_all()
        assert all_a["management_fee_rate"] == "8"
        assert all_a["tax_rate"] == "3.41"


class TestContextVarWorkspaceAwareness:
    """Context variable 传递测试：profile_tools通过context var获取workspace"""

    async def test_profile_tools_use_workspace_via_contextvar(self, tmp_path):
        """设置context var后，profile tools应使用workspace的profile"""
        from max_system.config.workspace import WorkspaceManager
        from max_system.tools.profile_tools import (
            profile_update, set_profile_manager,
        )
        from max_system.config.profile import ProfileManager

        base_dir = tmp_path / "workspaces"
        wm = WorkspaceManager(base_dir)
        await wm.initialize()
        ws = await wm.get_workspace("test_chat")

        # Set up the context var using the orchestrator's ContextVar
        from max_system.core.orchestrator import _current_workspace
        token = _current_workspace.set(ws)

        try:
            # Set profile manager to workspace profile (as orchestrator does)
            set_profile_manager(ws.profile)

            # Now profile_update should use workspace profile
            result = await profile_update({
                "key": "company_name",
                "value": "测试设计工作室",
            })
            assert "已更新" in result["content"][0]["text"]

            # Verify it went to the workspace DB
            assert await ws.profile.get("company_name") == "测试设计工作室"

            # Verify the global profile is unaware (different DB)
            global_db = tmp_path / "global.db"
            global_profile = ProfileManager(global_db)
            await global_profile.initialize()

            set_profile_manager(global_profile)
            assert await global_profile.is_empty()
        finally:
            _current_workspace.reset(token)
            set_profile_manager(None)

        await wm.close()


class TestBackwardCompatibility:
    """CLI模式无workspace时的向后兼容测试"""

    async def test_profile_tools_work_without_workspace(self, tmp_path):
        """不设置workspace时，profile tools应使用全局profile_manager"""
        from max_system.tools.profile_tools import (
            profile_get, profile_update, set_profile_manager, get_profile_manager,
        )
        from max_system.config.profile import ProfileManager

        db_path = tmp_path / "cli_test.db"
        mgr = ProfileManager(db_path)
        await mgr.initialize()
        set_profile_manager(mgr)

        # Update profile without any workspace context
        result = await profile_update({
            "key": "company_name",
            "value": "CLI测试公司",
        })
        assert "已更新" in result["content"][0]["text"]

        # Verify it was written
        assert await mgr.get("company_name") == "CLI测试公司"

        await mgr.close()

    async def test_clientmgr_without_workspace(self, tmp_path):
        """不设置workspace时，clientmgr应使用全局_clients_db"""
        from max_system.tools.clientmgr_tools import (
            clientmgr_create_client, clientmgr_query_clients,
            set_current_workspace,
        )

        # Clear workspace
        set_current_workspace("")

        # Create a client
        result = await clientmgr_create_client({
            "name": "张三",
            "phone": "13800138000",
            "city": "北京",
        })
        assert "已创建" in result["content"][0]["text"]
        assert "success" in result["content"][0]["text"]

        # Query it back
        result = await clientmgr_query_clients({"name": "张三"})
        assert "张三" in result["content"][0]["text"]

    async def test_clientmgr_workspace_isolation(self, tmp_path):
        """不同workspace的client数据隔离"""
        from max_system.tools.clientmgr_tools import (
            clientmgr_create_client, clientmgr_query_clients,
            set_current_workspace, _workspace_clients,
        )

        # Clear any previous workspace state
        _workspace_clients.clear()

        # Workspace A: create client
        set_current_workspace("company_a")
        await clientmgr_create_client({
            "name": "客户A",
            "phone": "111",
            "city": "北京",
        })

        # Workspace B: create different client
        set_current_workspace("company_b")
        await clientmgr_create_client({
            "name": "客户B",
            "phone": "222",
            "city": "上海",
        })

        # Query workspace B - should only see client B
        result = await clientmgr_query_clients({})
        data = result["content"][0]["text"]
        assert "客户B" in data
        assert "客户A" not in data

        # Query workspace A - should only see client A
        set_current_workspace("company_a")
        result = await clientmgr_query_clients({})
        data = result["content"][0]["text"]
        assert "客户A" in data
        assert "客户B" not in data

        # Cleanup
        set_current_workspace("")
        _workspace_clients.clear()


class TestWorkspaceKnowledgeIsolation:
    """知识库workspace隔离测试"""

    async def test_workspace_knowledge_create(self, tmp_path):
        """workspace创建knowledge目录"""
        from max_system.config.workspace import WorkspaceManager

        base_dir = tmp_path / "workspaces"
        wm = WorkspaceManager(base_dir)
        await wm.initialize()
        ws = await wm.get_workspace("chat_kb_test")

        # The workspace dir should exist
        assert ws.dir.exists()

        # Workspace knowledge dir should be defined but not auto-created
        assert ws.knowledge_path == ws.dir / "knowledge"
        assert not ws.knowledge_path.exists()  # Only created on first write

        await wm.close()

    async def test_workspace_knowledge_write(self, tmp_path):
        """写入workspace knowledge目录"""
        from max_system.config.workspace import WorkspaceManager

        base_dir = tmp_path / "workspaces"
        wm = WorkspaceManager(base_dir)
        await wm.initialize()
        ws = await wm.get_workspace("chat_kb_write")

        # Create knowledge dir manually (as knowledge_import would)
        ws.knowledge_path.mkdir(parents=True, exist_ok=True)
        test_file = ws.knowledge_path / "test.md"
        test_file.write_text("# Test Knowledge", encoding="utf-8")

        assert ws.knowledge_path.exists()
        assert test_file.exists()

        await wm.close()
