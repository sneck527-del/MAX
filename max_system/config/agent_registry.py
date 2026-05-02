"""Agent注册表：目录映射与工具权限配置"""

from max_system.config.settings import MaxSettings


# Agent目录映射：Agent名称 → (目录名, 技能子目录列表, 功能描述)
# 每个Agent都有中文名+英文名，方便在对话中称呼
AGENT_SPECS = {
    "talker": (
        "02_Talker谈单官",
        ["skill_01_LeadCatch", "skill_02_NeedAnaly", "skill_03_TalkScript",
         "skill_04_PlanPro", "skill_05_ContractPro", "skill_06_DataStat"],
        "晓言Neo：拓客谈单官 — 客户线索获取、需求分析、谈单话术、谈判策划、合同辅助、数据统计",
    ),
    "afterpro": (
        "03_AfterPro售后官",
        ["skill_01_ReturnVisit", "skill_02_IssueFix", "skill_03_AfterLog",
         "skill_04_ClientCare", "skill_05_ComplaintPro"],
        "安馨Lumi：售后维护官 — 竣工回访、问题处理、售后台账、老客户维护、客诉处理",
    ),
    "mediapro": (
        "04_MediaPro自媒体",
        ["skill_01_ContentGen", "skill_02_CasePack", "skill_03_AccountOpt",
         "skill_04_LeadTransfer", "skill_05_DataReview"],
        "墨羽Kai：自媒体增长官 — 文案生成、案例包装、账号运营、线索转化、内容复盘",
    ),
    "helper": (
        "05_Helper执行助手",
        ["skill_01_DocGen", "skill_02_ClientMgr", "skill_03_Knowledge",
         "skill_04_FeishuLink", "skill_05_ObsidianSync"],
        "力行Rex：执行助手 — 文档生成、客户管理、知识库调用、飞书交互、归档同步",
    ),
}

# 每个Agent可使用的MCP工具
AGENT_TOOLS = {
    "talker": [
        "feishu_send_message", "feishu_read_bitable", "feishu_write_bitable",
        "knowledge_search", "obsidian_archive_note", "obsidian_search_vault",
        "clientmgr_create_client", "clientmgr_update_client", "clientmgr_query_clients",
        "docgen_generate_doc", "quote_query_materials", "quote_query_construction",
        "leadcatch_classify", "needanaly_report", "talkscript_generate",
        "planpro_create", "contractpro_draft", "datastat_report",
    ],
    "afterpro": [
        "feishu_send_message", "feishu_read_bitable", "feishu_write_bitable",
        "knowledge_search", "obsidian_archive_note", "obsidian_search_vault",
        "clientmgr_update_client", "clientmgr_query_clients",
        "docgen_generate_doc",
        "returnvisit_schedule", "issuefix_track", "afterlog_update",
        "clientcare_reminder", "complaintpro_handle",
    ],
    "mediapro": [
        "feishu_send_message", "feishu_read_bitable",
        "knowledge_search", "obsidian_archive_note", "obsidian_search_vault",
        "clientmgr_query_clients",
        "docgen_generate_doc",
        "contentgen_draft", "casepack_package", "accountopt_plan",
        "leadtransfer_qualify", "datareview_analyze",
    ],
    "helper": [
        "feishu_send_message", "feishu_read_bitable", "feishu_write_bitable",
        "feishu_create_approval", "feishu_create_calendar_event",
        "knowledge_search", "knowledge_compliance_check",
        "obsidian_archive_note", "obsidian_search_vault", "obsidian_read_note",
        "clientmgr_create_client", "clientmgr_update_client", "clientmgr_query_clients",
        "docgen_generate_doc", "docgen_validate_doc",
        "quote_query_materials", "quote_query_construction",
        "helper_batch_generate", "helper_client_tag_and_report",
        "helper_knowledge_catalog", "helper_feishu_sync_alert",
        "helper_obsidian_full_archive",
    ],
}
