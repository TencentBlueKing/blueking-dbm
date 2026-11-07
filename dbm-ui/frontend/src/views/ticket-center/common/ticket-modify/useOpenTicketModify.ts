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

/**
 * 在当前页跳转到改单工具页：申请页路由（与单据类型同名）带 ticketId 与 modifyMode
 * 申请页与单据详情都是不带业务前缀的全局路由，同页跳转不需要切换业务；
 * 与「再次提单」共用 ticketId 回填，靠 modifyMode 区分是否为改单
 */
export default function useOpenTicketModify() {
  const router = useRouter();

  return (ticketData: Pick<TicketModel, 'id' | 'ticket_type'>, mode: TicketModifyMode) => {
    router.push({
      name: ticketData.ticket_type,
      query: {
        modifyMode: mode,
        ticketId: ticketData.id,
      },
    });
  };
}
