"""Max系统全局配置管理"""

from pathlib import Path

from pydantic_settings import BaseSettings


class MaxSettings(BaseSettings):
    """从 .env 文件和环境变量加载所有配置"""

    # LLM配置 - DeepSeek（云端）
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.3
    llm_max_turns: int = 50

    # LLM配置 - Ollama（本地）
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "qwen3.5"
    ollama_api_key: str = "ollama"  # Ollama不需要key，但SDK要求非空

    # 默认LLM提供者: "deepseek" 或 "ollama"
    llm_provider: str = "deepseek"

    # 飞书开放平台
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_verification_token: str = ""
    feishu_encrypt_key: str = ""
    feishu_bitable_app_token: str = ""

    # 多维表格各表ID
    # 线上已有表
    bitable_table_clients: str = "tbl6IdYFBB8RDFiO"        # 客户信息
    bitable_table_contracts: str = "tblRS5zg0u5Hj6DN"      # 合同管理
    bitable_table_suppliers: str = "tblnKdukg33OfUsN"      # 合作商
    bitable_table_expense: str = "tbl2X6WH1RuCwBM3"        # 支出明细
    bitable_table_income: str = "tbl6WFZYHS19JHKk"         # 收入明细
    bitable_table_construction: str = "tblLBj0GQik63K9W"   # 施工管理
    bitable_table_tasks: str = "tblZA6hpoSVUbfTm"           # 任务
    # 待新建表（init_bitable.py 创建后填入）
    bitable_table_after_sales: str = ""                     # 售后维保台账
    bitable_table_followups: str = ""                       # 跟进记录表（回访+跟进合并）

    # Obsidian
    obsidian_vault_path: Path = Path("M:/ObsidianVault/斑马精装")

    # 知识库
    knowledge_base_path: Path = Path("M:/ClaudeCode/06_知识库")
    vector_store_path: Path = Path("M:/ClaudeCode/06_知识库/.vector_index")

    # 报价数据
    quote_data_path: Path = Path("M:/ClaudeCode/Quote")

    # 项目路径
    project_root: Path = Path("M:/ClaudeCode")
    prompts_root: Path = Path("M:/ClaudeCode")
    audit_db_path: Path = Path("M:/ClaudeCode/01_Max总控/log_audit/audit.db")

    # Webhook服务
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8080

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


_settings: MaxSettings | None = None


def get_settings() -> MaxSettings:
    global _settings
    if _settings is None:
        _settings = MaxSettings()
    return _settings
