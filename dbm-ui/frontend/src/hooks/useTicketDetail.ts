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
import { useRequest } from 'vue-request';
import { useRoute } from 'vue-router';

import type { DetailBase } from '@services/model/ticket/details/common';
import TicketModel from '@services/model/ticket/ticket';
import { getTicketDetails } from '@services/source/ticket';

import { TicketTypes } from '@common/const';

export function useTicketDetail<T extends DetailBase>(
  ticketType: TicketTypes,
  options: {
    onSuccess: (data: TicketModel<T>) => void;
  },
) {
  const route = useRoute();
  const { ticketId } = route.query;

  if (!ticketId) {
    return;
  }

  useRequest(getTicketDetails, {
    defaultParams: [{ id: Number(ticketId) }, { permission: 'catch' }],
    onSuccess(ticketData) {
      if (ticketType !== ticketData.ticket_type) {
        return;
      }
      options.onSuccess(ticketData as TicketModel<T>);
    },
  });
}
