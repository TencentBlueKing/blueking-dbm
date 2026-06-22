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
  [ClusterTypes.K8S_QDRANT_HA]: TicketTypes.K8S_QDRANT_RESTART,
  [ClusterTypes.K8S_SURREALDB]: TicketTypes.K8S_SURREALDB_RESTART,
} as const;

export function useK8sClusterRestart(clusterType: keyof typeof ticketTypeMap, options: { onSuccess: () => void }) {
  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const handleClusterRestart = (data: { cluster_name: string; id: number }) => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('重启'),
      content: `${t('集群名称：')}${data.cluster_name}`,
      onConfirm: () => {
        createTicket({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          details: {
            cluster_id: data.id,
          },
          remark: '',
          ticket_type: ticketTypeMap[clusterType],
        }).then((ticketResult) => {
          ticketMessage(ticketResult.id);
          options.onSuccess();
        });
      },
      title: t('确认重启该集群？'),
      width: 400,
    });
  };

  return {
    handleClusterRestart,
  };
}
