"""Max系统全局配置管理"""

from pathlib import Path

from pydantic_settings import BaseSettings

# 项目根目录（max_system的上级）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


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
    ollama_api_key: str = "ollama"

    # 默认LLM提供者: "deepseek" 或 "ollama"
    llm_provider: str = "deepseek"

    # 飞书开放平台
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_verification_token: str = ""
    feishu_encrypt_key: str = ""
    feishu_bitable_app_token: str = ""

    # 多维表格各表ID（由 max init 自动创建填入，也可手动填写）
    bitable_table_clients: str = ""
    bitable_table_contracts: str = ""
    bitable_table_suppliers: str = ""
    bitable_table_expense: str = ""
    bitable_table_income: str = ""
    bitable_table_construction: str = ""
    bitable_table_tasks: str = ""
    bitable_table_after_sales: str = ""
    bitable_table_followups: str = ""

    # 知识库（空值=项目根/knowledge）
    knowledge_base_path: Path = Path("")
    vector_store_path: Path = Path("")

    # 报价数据（空值=项目根/quotes）
    quote_data_path: Path = Path("")

    # 项目路径（自动推断，留空即可）
    project_root: Path = Path("")
    prompts_root: Path = Path("")

    # 数据库（空值=项目根/data/max.db）
    db_path: Path = Path("")

    # 主动提醒推送目标（设计师的飞书 chat_id，用于早晚报/到期提醒）
    notification_chat_id: str = ""

    # ARK Design 集成
    ark_project_path: Path = Path(__file__).resolve().parent.parent.parent / "ark_design"
    ark_node_path: str = "node"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def _is_set(self, p: Path) -> bool:
        """检查路径是否被用户显式设置（非空非当前目录）"""
        s = str(p)
        return bool(s) and s != "."

    def get_project_root(self) -> Path:
        return self.project_root if self._is_set(self.project_root) else _PROJECT_ROOT

    def get_prompts_root(self) -> Path:
        return self.prompts_root if self._is_set(self.prompts_root) else _PROJECT_ROOT / "prompts"

    def get_knowledge_base_path(self) -> Path:
        return self.knowledge_base_path if self._is_set(self.knowledge_base_path) else self.get_project_root() / "knowledge"

    def get_quote_data_path(self) -> Path:
        return self.quote_data_path if self._is_set(self.quote_data_path) else self.get_project_root() / "quotes"

    def get_db_path(self) -> Path:
        return self.db_path if self._is_set(self.db_path) else self.get_project_root() / "data" / "max.db"


_settings: MaxSettings | None = None


def get_settings() -> MaxSettings:
    global _settings
    if _settings is None:
        _settings = MaxSettings()
    return _settings
