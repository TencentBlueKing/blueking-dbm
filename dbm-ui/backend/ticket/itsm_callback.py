"""ITSM 回调凭证，绑定 DBM 单据，避免跨单据使用。"""

import logging

from django.utils.crypto import constant_time_compare
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
    token = data.get("token")
    if not isinstance(token, str) or not token:
        logger.warning(_("ITSM 回调被拒绝：单据 ID=%s，原因=回调凭证缺失或格式错误"), ticket.pk)
        raise PermissionDenied(_("ITSM 回调凭证缺失或格式错误"))

    if version == ItsmApiAdapter.V4:
        if not constant_time_compare(token, get_callback_token(ticket.pk)):
            logger.warning(_("ITSM 回调被拒绝：单据 ID=%s，版本=v4，原因=回调凭证不匹配"), ticket.pk)
            raise PermissionDenied(_("无效的 ITSM 回调凭证"))
    else:
        # 组件接口已解包外层响应，此处读取 data 中的校验结果。
        result = ItsmApiAdapter.verify_token({"token": token}, use_admin=True)
        if not isinstance(result, dict) or result.get("is_passed") is not True:
            logger.warning(_("ITSM 回调被拒绝：单据 ID=%s，版本=v3，原因=回调凭证无效"), ticket.pk)
            raise PermissionDenied(_("无效的 ITSM 回调凭证"))
    logger.info(_("ITSM 回调校验通过：单据 ID=%s，版本=%s"), ticket.pk, version)
