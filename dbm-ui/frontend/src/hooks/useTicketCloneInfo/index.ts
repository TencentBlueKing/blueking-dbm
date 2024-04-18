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

import { getTicketDetails } from '@services/source/ticket';

import { type CloneDataHandlerMap, type CloneDataHandlerMapKeys, generateCloneData } from './generateCloneData';

export function useTicketCloneInfo<T extends CloneDataHandlerMapKeys>(params: {
  type: T;
  onSuccess?: (data: ServiceReturnType<CloneDataHandlerMap[T]>, ticketType: T) => void;
}) {
  const { type, onSuccess } = params;
  const route = useRoute();
  const ticketId = route.query.ticket_id;

  const data = ref<ServiceReturnType<CloneDataHandlerMap[T]>>();

  if (!ticketId) {
    return { data };
  }

  useRequest(getTicketDetails, {
    defaultParams: [{ id: Number(ticketId) }, { permission: 'catch' }],
    async onSuccess(ticketData) {
      if (type !== ticketData.ticket_type) {
        return;
      }

      data.value = await generateCloneData(type, ticketData);
      if (onSuccess) {
        onSuccess(data.value, type);
      }
    },
  });

  return { data };
}
