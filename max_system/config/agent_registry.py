"""工具注册表：所有工具模块的注册入口"""

from max_system.config.settings import MaxSettings


def register_all_tools(settings: MaxSettings) -> list[tuple[str, callable, dict]]:
    """注册所有工具，返回 [(name, callable, tool_def)]"""
    from max_system.tools.feishu_tools import register_tools as reg_feishu
    from max_system.tools.knowledge_tools import register_tools as reg_knowledge
    from max_system.tools.quote_tools import register_tools as reg_quote
    from max_system.tools.clientmgr_tools import register_tools as reg_clientmgr
    from max_system.tools.sales_tools import register_tools as reg_sales
    from max_system.tools.service_tools import register_tools as reg_service
    from max_system.tools.marketing_tools import register_tools as reg_marketing
    from max_system.tools.profile_tools import register_tools as reg_profile
    from max_system.tools.schedule_tools import register_tools as reg_schedule
    from max_system.tools.document_tools import register_tools as reg_document
    from max_system.tools.project_tools import register_tools as reg_project
    from max_system.tools.reminder_tools import register_tools as reg_reminder
    from max_system.tools.ark_bridge import register_tools as reg_ark
    from max_system.tools.construction_tools import register_tools as reg_construction

    tools = []
    for reg_fn in [reg_feishu, reg_knowledge, reg_quote,
                   reg_clientmgr, reg_sales, reg_service, reg_marketing,
                   reg_profile, reg_schedule, reg_document, reg_project,
                   reg_reminder, reg_ark, reg_construction]:
        tools.extend(reg_fn(settings))
    return tools
