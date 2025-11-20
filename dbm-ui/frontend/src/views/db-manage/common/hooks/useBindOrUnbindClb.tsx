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
  [ClusterTypes.ES]: {
    bind: TicketTypes.ES_DNS_BIND_CLB,
    unbind: TicketTypes.ES_DNS_UNBIND_CLB,
  },
  [ClusterTypes.REDIS_CLUSTER]: {
    bind: TicketTypes.REDIS_PLUGIN_DNS_BIND_CLB,
    unbind: TicketTypes.REDIS_PLUGIN_DNS_UNBIND_CLB,
  },
  [ClusterTypes.TENDBCLUSTER]: {
    bind: TicketTypes.TENDBCLUSTER_CLB_BIND_DOMAIN,
    unbind: TicketTypes.TENDBCLUSTER_CLB_UNBIND_DOMAIN,
  },
  [ClusterTypes.TENDBHA]: {
    bind: TicketTypes.MYSQL_CLB_BIND_DOMAIN,
    unbind: TicketTypes.MYSQL_CLB_UNBIND_DOMAIN,
  },
} as const;

export function useBindOrUnbindClb<T>(clusterType: keyof typeof ticketTypeMap) {
  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const handleBindOrUnbindClb = (formData: { details: T; remark?: string }, isBind: boolean) => {
    const title = isBind ? t('确认恢复 DNS 域名指向？') : t('确认将 DNS 域名指向 CLB ?');
    const content = isBind ? t('DNS 域名恢复指向 Proxy') : t('业务不需要更换原域名也可实现负载均衡');
    const ticketType = isBind ? ticketTypeMap[clusterType].unbind : ticketTypeMap[clusterType].bind;

    InfoBox({
      content,
      onConfirm: () => {
        createTicket({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          details: formData.details,
          remark: formData.remark || '',
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
    handleBindOrUnbindClb,
  };
}
