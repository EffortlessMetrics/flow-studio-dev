"""
Flow Studio configuration module.

Provides FlowStudioConfig dataclass for managing Flow Studio paths.
Simplified version for standalone deployment.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FlowStudioConfig:
    """
    Configuration for Flow Studio paths and settings.

    All paths are absolute Path objects. Use from_project_root() to construct
    from a project root path.

    Attributes:
        project_root: Root of the project
        flows_dir: Directory containing flow YAML configs
        agents_dir: Directory containing agent YAML configs
    """

    project_root: Path
    flows_dir: Path
    agents_dir: Path

    @classmethod
    def from_project_root(cls, project_root: Path) -> "FlowStudioConfig":
        """
        Construct config from a project root path.

        Args:
            project_root: Path to the project root

        Returns:
            FlowStudioConfig with all paths resolved
        """
        project_root = project_root.resolve()
        return cls(
            project_root=project_root,
            flows_dir=project_root / "config" / "flows",
            agents_dir=project_root / "config" / "agents",
        )

    @classmethod
    def from_file(cls, file_path: Path, levels_up: int = 1) -> "FlowStudioConfig":
        """
        Construct config from a file path by walking up directories.

        This is useful for constructing config from __file__ in scripts.

        Args:
            file_path: Path to a file (e.g., __file__)
            levels_up: Number of parent directories to walk up (default: 1)

        Returns:
            FlowStudioConfig with all paths resolved
        """
        project_root = Path(file_path).resolve()
        for _ in range(levels_up):
            project_root = project_root.parent
        return cls.from_project_root(project_root)

    def validate(self) -> list[str]:
        """
        Validate that required directories exist.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if not self.project_root.exists():
            errors.append(f"project_root does not exist: {self.project_root}")
            return errors  # Can't check others if root missing

        if not self.flows_dir.exists():
            errors.append(f"flows_dir does not exist: {self.flows_dir}")

        if not self.agents_dir.exists():
            errors.append(f"agents_dir does not exist: {self.agents_dir}")

        return errors

    def list_flows(self) -> list[Path]:
        """List all flow YAML files."""
        if not self.flows_dir.exists():
            return []
        return sorted(self.flows_dir.glob("*.yaml"))

    def list_agents(self) -> list[Path]:
        """List all agent YAML files."""
        if not self.agents_dir.exists():
            return []
        return sorted(self.agents_dir.glob("*.yaml"))


# Default config instance (lazily constructed)
_DEFAULT_CONFIG: Optional[FlowStudioConfig] = None


def get_default_config() -> FlowStudioConfig:
    """
    Get the default FlowStudioConfig for this project.

    Lazily constructs the config on first call.
    """
    global _DEFAULT_CONFIG
    if _DEFAULT_CONFIG is None:
        _DEFAULT_CONFIG = FlowStudioConfig.from_file(Path(__file__), levels_up=1)
    return _DEFAULT_CONFIG
