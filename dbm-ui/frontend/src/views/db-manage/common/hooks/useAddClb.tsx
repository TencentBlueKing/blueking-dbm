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

import { createTicket } from '@services/source/ticket';

import { useTicketMessage } from '@hooks';

import { ClusterTypes, TicketTypes } from '@common/const';

const ticketTypeMap = {
  [ClusterTypes.ES]: TicketTypes.ES_CREATE_CLB,
  [ClusterTypes.MONGO_SHARED_CLUSTER]: TicketTypes.MONGODB_PLUGIN_CREATE_CLB,
  [ClusterTypes.REDIS_CLUSTER]: TicketTypes.REDIS_PLUGIN_CREATE_CLB,
  [ClusterTypes.TENDBCLUSTER]: TicketTypes.TENDBCLUSTER_ADD_CLB,
  [ClusterTypes.TENDBHA]: TicketTypes.MYSQL_ADD_CLB,
} as const;

export function useAddClb<T>(clusterType: keyof typeof ticketTypeMap) {
  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const handleAddClb = (formData: { details: T; remark?: string }) => {
    InfoBox({
      content: t('启用 CLB 之后，该集群可以通过 CLB 来访问'),
      onConfirm: () => {
        createTicket({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          details: formData.details,
          remark: formData.remark || '',
          ticket_type: ticketTypeMap[clusterType],
        }).then((ticketResult) => {
          ticketMessage(ticketResult.id);
        });
      },
      title: t('确定启用 CLB？'),
      width: 400,
    });
  };

  return {
    handleAddClb,
  };
}
