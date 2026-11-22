"""Import all models so SQLAlchemy / Alembic can discover metadata."""

from app.models.audit import AuditLog
from app.models.incident import (
    AIInvestigation,
    AgentExecution,
    ExecutedAction,
    FirewallRule,
    ResponseRecommendation,
    SecurityIncident,
)
from app.models.ml import Dataset, MLModel, Prediction, TrainingRun
from app.models.network import NetworkEvent, PcapFile, TrafficRecord
from app.models.user import AppSetting, User, UserActivity
from app.models.automation import (
    AppNotification,
    AutomationDedupe,
    AutomationWorkflow,
    NotificationRule,
    ResponseAutomationPolicy,
    ScheduledTask,
    ScheduledTaskRun,
    WorkflowExecution,
)

__all__ = [
    "User",
    "UserActivity",
    "AppSetting",
    "PcapFile",
    "TrafficRecord",
    "NetworkEvent",
    "Dataset",
    "MLModel",
    "TrainingRun",
    "Prediction",
    "SecurityIncident",
    "AIInvestigation",
    "AgentExecution",
    "ResponseRecommendation",
    "ExecutedAction",
    "FirewallRule",
    "AuditLog",
    "AutomationWorkflow",
    "WorkflowExecution",
    "ScheduledTask",
    "ScheduledTaskRun",
    "AppNotification",
    "NotificationRule",
    "ResponseAutomationPolicy",
    "AutomationDedupe",
]
