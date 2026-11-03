"""ITSM 回调凭证，绑定 DBM 单据，避免跨单据使用。"""

import logging

from django.utils.translation import gettext as _
from rest_framework.exceptions import PermissionDenied

from backend.components import ItsmApiAdapter
from backend.components.itsm.backends.v4 import ItsmV4Backend
from backend.ticket.constants import FlowType

logger = logging.getLogger("ticket.itsm_callback")


def get_callback_token(ticket_id):
    return ItsmV4Backend.get_callback_token(ticket_id)


def verify_callback(ticket, data):
    flow = ticket.current_flow()
    if not flow or flow.flow_type != FlowType.BK_ITSM or not flow.flow_obj_id:
        logger.warning(_("ITSM 回调被拒绝：单据 ID=%s，原因=没有已创建的当前 ITSM 流程"), ticket.pk)
        raise PermissionDenied(_("无效的 ITSM 回调"))

    version = ItsmApiAdapter._get_itsm_version_by_sn(flow.flow_obj_id)
    logger.info(
        _("开始校验 ITSM 回调：单据 ID=%s，ITSM 单号=%s，版本=%s"),
        ticket.pk,
        flow.flow_obj_id,
        version,
    )
    try:
        ItsmApiAdapter.verify_callback(ticket.pk, flow.flow_obj_id, data)
    except PermissionDenied as exc:
        logger.warning(_("ITSM 回调被拒绝：单据 ID=%s，版本=%s，原因=%s"), ticket.pk, version, exc.detail)
        raise
    logger.info(_("ITSM 回调校验通过：单据 ID=%s，版本=%s"), ticket.pk, version)
