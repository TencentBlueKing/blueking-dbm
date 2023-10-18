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

import {
  onBeforeUnmount,
  ref } from 'vue';

// TODO INTERFACE
import {
  getTaskflowDetails,
} from '@services/taskflow';


export default function (rootId: string) {
  const status = ref('RUNNING');
  const ticketId = ref('');

  const statusText = computed(() => {
    if (['RUNNING', 'CREATED'].includes(status.value)) {
      return 'pending';
    } if (status.value === 'FINISHED') {
      return 'successed';
    }
    return 'failed';
  });

  let timer = 0;

  const fetchStatus = () => {
    getTaskflowDetails({
      rootId,
    }).then((data) => {
      status.value = data.flow_info.status;
      ticketId.value = data.flow_info.uid;
      if (timer < 0) {
        return;
      }
      if (statusText.value === 'pending') {
        timer = setTimeout(() => {
          fetchStatus();
        }, 2000);
      }
    });
  };

  fetchStatus();

  onBeforeUnmount(() => {
    clearTimeout(timer);
    timer = -1;
  });

  return {
    flowStatus: statusText,
    ticketId,
  };
}
