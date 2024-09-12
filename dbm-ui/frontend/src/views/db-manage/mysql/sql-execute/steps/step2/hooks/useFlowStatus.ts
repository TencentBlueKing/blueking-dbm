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

import { onBeforeUnmount, ref } from 'vue';
import { useRequest } from 'vue-request';

import { getTaskflowDetails } from '@services/source/taskflow';

export default function (rootId: string) {
  const status = ref('RUNNING');
  const ticketId = ref('');

  const statusText = computed(() => {
    if (['RUNNING', 'CREATED'].includes(status.value)) {
      return 'pending';
    }
    if (status.value === 'FINISHED') {
      return 'successed';
    }
    return 'failed';
  });

  const { cancel } = useRequest(getTaskflowDetails, {
    pollingInterval: 2000,
    defaultParams: [
      {
        rootId,
      },
    ],
    onSuccess: (data) => {
      status.value = data.flow_info.status;
      ticketId.value = data.flow_info.uid;
      if (statusText.value !== 'pending') {
        cancel();
      }
    },
  });

  onBeforeUnmount(() => {
    cancel();
  });

  return {
    flowStatus: statusText,
    ticketId,
  };
}
