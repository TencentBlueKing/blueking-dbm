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
  [ClusterTypes.MONGO_SHARED_CLUSTER]: {
    create: TicketTypes.MONGODB_PLUGIN_CREATE_CLB,
    delete: TicketTypes.MONGODB_PLUGIN_DELETE_CLB,
  },
  [ClusterTypes.REDIS_CLUSTER]: {
    create: TicketTypes.REDIS_PLUGIN_CREATE_CLB,
    delete: TicketTypes.REDIS_PLUGIN_DELETE_CLB,
  },
} as const;

export const useSwitchClb = (clusterType: keyof typeof ticketTypeMap) => {
  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const handleSwitchClb = (data: { id: number; isOnlineCLB: boolean }) => {
    const title = data.isOnlineCLB ? t('确定禁用CLB？') : t('确定启用CLB？');
    const content = data.isOnlineCLB
      ? t('禁用 CLB 之后，该集群仍可通过域名来访问')
      : t('启用 CLB 之后，该集群可以通过 CLB 来访问');
    const ticketType = data.isOnlineCLB ? ticketTypeMap[clusterType].delete : ticketTypeMap[clusterType].create;

    InfoBox({
      content,
      onConfirm: () => {
        createTicket({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          details: {
            cluster_id: data.id,
          },
          ticket_type: ticketType,
        }).then((ticketResult) => {
          ticketMessage(ticketResult.id);
        });
      },
      title,
      width: 400,
    });
  };

  return {
    handleSwitchClb,
  };
};
