"""Workspace Manager — per-chat data isolation for multi-tenant deployments.

Each workspace (identified by chat_id) gets its own:
- SQLite database (data/workspaces/{workspace_id}/max.db)
- ProfileManager pointing to that DB
- Optional knowledge base directory

Workspaces are cached in memory for the lifetime of the process.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from max_system.config.profile import ProfileManager

logger = logging.getLogger(__name__)


class Workspace:
    """A single design company's isolated data space."""

    def __init__(self, workspace_id: str, base_dir: Path):
        self.workspace_id = workspace_id
        self.dir = base_dir / workspace_id
        self.db_path = self.dir / "max.db"
        self.knowledge_path = self.dir / "knowledge"
        self.quotes_path = self.dir / "quotes"
        self.created_at = datetime.now(timezone.utc).isoformat()

        self.profile: ProfileManager | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Create the workspace directory and initialize the per-workspace ProfileManager."""
        if self._initialized:
            return

        self.dir.mkdir(parents=True, exist_ok=True)
        self.profile = ProfileManager(self.db_path)
        await self.profile.initialize()
        self._initialized = True
        logger.info("Workspace initialized: %s -> %s", self.workspace_id, self.db_path)

    async def close(self) -> None:
        """Close the workspace database connection."""
        if self.profile:
            await self.profile.close()
            self.profile = None
        self._initialized = False


class WorkspaceManager:
    """Manages per-workspace (per-chat) data isolation.

    Usage:
        wm = WorkspaceManager(settings.get_project_root() / "data" / "workspaces")
        await wm.initialize()
        workspace = await wm.get_workspace(chat_id)
        # use workspace.profile for profile operations
    """

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self._workspaces: dict[str, Workspace] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Ensure the base directory exists."""
        if self._initialized:
            return
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._initialized = True
        logger.info("WorkspaceManager initialized at %s", self.base_dir)

    async def get_workspace(self, workspace_id: str) -> Workspace:
        """Get or create a workspace for the given chat_id."""
        if not self._initialized:
            await self.initialize()

        if workspace_id not in self._workspaces:
            ws = Workspace(workspace_id, self.base_dir)
            await ws.initialize()
            self._workspaces[workspace_id] = ws
            logger.info("Created new workspace: %s", workspace_id)

        return self._workspaces[workspace_id]

    async def close(self) -> None:
        """Close all workspace database connections."""
        for ws in self._workspaces.values():
            await ws.close()
        self._workspaces.clear()
        logger.info("WorkspaceManager closed")
