/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */
import type { TicketModifyMode } from '@services/model/ticket/modify-record';
import type TicketModel from '@services/model/ticket/ticket';

import { getBusinessHref } from '@utils';

/**
 * 在新标签页打开改单工具页：申请页路由（与单据类型同名）带 ticketId 与 modifyMode
 * 与「再次提单」共用 ticketId 回填，靠 modifyMode 区分是否为改单
 */
export default function useOpenTicketModify() {
  const router = useRouter();

  return (ticketData: Pick<TicketModel, 'bk_biz_id' | 'id' | 'ticket_type'>, mode: TicketModifyMode) => {
    const { href } = router.resolve({
      name: ticketData.ticket_type,
      query: {
        modifyMode: mode,
        ticketId: ticketData.id,
      },
    });
    window.open(getBusinessHref(href, ticketData.bk_biz_id));
  };
}
