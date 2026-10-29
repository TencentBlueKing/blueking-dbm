"""DTS 退池前核对独立备份下载，流程终止不代表备份服务停止写入。"""

from django.utils.translation import gettext as _

from backend.components.mysql_backup.client import MysqlBackupApi
from backend.db_services.taskflow.handlers import TaskFlowHandler
from backend.flow.consts import PENDING_STATES, StateType
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.models import FlowNode, FlowTree


class BackupDownloadPending(Exception):
    """下载仍在进行或无法证明已经停止，保持回收步骤失败以供重试。"""


def _download_records(engine: BambooEngine, root_id: str, node_id: str) -> list[dict]:
    nodes = list(FlowNode.objects.filter(root_id=root_id, node_id=node_id))
    if not nodes or any(node.is_expired for node in nodes):
        raise BackupDownloadPending(_("下载节点 {} 的运行记录缺失或已过期").format(node_id))
    history = engine.get_node_histories(node_id=node_id)
    if not history.result or not isinstance(history.data, list):
        raise BackupDownloadPending(_("无法读取下载节点 {} 的重试历史").format(node_id))
    started_nodes = [node for node in nodes if node.started_at or node.status not in PENDING_STATES]
    if not started_nodes and not history.data:
        return []

    state = engine.get_node_state(node_id=node_id)
    current = engine.get_node_execution_data(node_id=node_id)
    if state is None or not current.result or not isinstance(current.data, dict):
        raise BackupDownloadPending(_("无法读取下载节点 {} 的执行结果").format(node_id))
    records = [*history.data, {**current.data, "version": state.version}]
    versions = {record["version"] for record in records}
    if any(node.version_id and node.version_id not in versions for node in started_nodes):
        raise BackupDownloadPending(_("下载节点 {} 的部分执行历史已缺失").format(node_id))
    return records


def _ensure_bill_finished(record: dict, node_id: str, checked: set[tuple[int, int]]) -> None:
    kwargs = (record.get("inputs") or {}).get("kwargs") or {}
    bill_id = (record.get("outputs") or {}).get("backup_bill_id")
    cloud_id = kwargs.get("bk_cloud_id")
    if not isinstance(bill_id, int) or isinstance(bill_id, bool) or bill_id <= 0 or cloud_id is None:
        raise BackupDownloadPending(_("下载节点 {} 缺少下载单据 ID 或云区域，无法确认是否仍有下载，请核查后重试").format(node_id))
    key = (int(cloud_id), bill_id)
    if key in checked:
        return
    response = MysqlBackupApi.download_result({"bill_id": bill_id, "bk_cloud_id": cloud_id})
    total = response.get("total") if isinstance(response, dict) else None
    if not isinstance(total, dict) or any(
        not isinstance(total.get(name), int) or isinstance(total[name], bool) or total[name] < 0
        for name in ("todo", "doing", "fail")
    ):
        raise BackupDownloadPending(_("下载单据 {} 的状态不完整，不能回收主机").format(bill_id))
    if total["todo"] or total["doing"]:
        raise BackupDownloadPending(
            _("主机 {}（云区域 {}）的下载单据 {} 尚未结束：待执行 {}，执行中 {}，请等待后重试").format(
                kwargs.get("dest_ip", ""), cloud_id, bill_id, total["todo"], total["doing"]
            )
        )
    checked.add(key)


def ensure_backup_downloads_finished(root_id: str) -> None:
    """核对所有下载节点及重试历史；未知/排队/运行中的下载一律阻断清理。"""
    try:
        flow_tree = FlowTree.objects.get(root_id=root_id)
        if flow_tree.is_expired or flow_tree.status not in (StateType.REVOKED.value, StateType.FINISHED.value):
            raise BackupDownloadPending(_("原迁移流程 {} 尚未停止或运行数据已过期").format(root_id))
        if not isinstance(flow_tree.tree, dict):
            raise BackupDownloadPending(_("原迁移流程 {} 的流程树缺失").format(root_id))
        node_ids = TaskFlowHandler.get_node_id_by_component(flow_tree.tree, "mysql_download_backup_file")
        engine = BambooEngine(root_id=root_id)
        checked = set()
        for node_id in node_ids:
            for record in _download_records(engine, root_id, node_id):
                _ensure_bill_finished(record, node_id, checked)
    except BackupDownloadPending:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise BackupDownloadPending(_("无法确认原迁移流程 {} 的备份下载已停止: {}").format(root_id, exc)) from exc
