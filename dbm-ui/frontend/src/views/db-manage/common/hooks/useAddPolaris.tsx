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

import { InfoBox } from 'bkui-vue';
import { useI18n } from 'vue-i18n';

import { useCreateTicket } from '@hooks';

import { ClusterTypes, TicketTypes } from '@common/const';

const ticketTypeMap = {
  [ClusterTypes.ES]: TicketTypes.ES_CREATE_POLARIS,
  [ClusterTypes.REDIS_CLUSTER]: TicketTypes.REDIS_PLUGIN_CREATE_POLARIS,
} as const;

export function useAddPolaris<T>(clusterType: keyof typeof ticketTypeMap) {
  const { t } = useI18n();
  const { run: createTicketRun } = useCreateTicket<T>(ticketTypeMap[clusterType], {
    isToolbox: false,
    successMessage: t('操作提交成功'),
  });

  const handleAddPolaris = (formData: { details: T; remark?: string }) => {
    InfoBox({
      onConfirm: () => {
        createTicketRun({
          details: formData.details,
          remark: formData.remark,
        });
      },
      title: t('确定启用北极星？'),
      width: 400,
    });
  };

  return {
    handleAddPolaris,
  };
}
