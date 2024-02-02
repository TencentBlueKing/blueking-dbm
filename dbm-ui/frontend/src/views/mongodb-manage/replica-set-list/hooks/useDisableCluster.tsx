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

import { useI18n } from 'vue-i18n';

import { createTicket } from '@services/source/ticket';

import {
  useInfoWithIcon,
  useTicketMessage,
} from '@hooks';

import { useGlobalBizs } from '@stores';

import { TicketTypes } from '@common/const';


export const useDisableCluster = () => {
  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const diabledCluster = (data: {
    cluster_name: string,
    id: number
  }) => {
    useInfoWithIcon({
      type: 'warnning',
      title: t('确定禁用该集群'),
      content: () => (
        <>
          <p>{ t('集群') }：<span class='info-box-cluster-name'>{ data.cluster_name }</span></p>
          <p>{ t('被禁用后将无法访问，如需恢复访问，可以再次「启用」') }</p>
        </>
      ),
      confirmTxt: t('禁用'),
      onConfirm: async () => {
        try {
          await createTicket({
            bk_biz_id: currentBizId,
            ticket_type: TicketTypes.MONGODB_DISABLE,
            details: {
              cluster_ids: [data.id],
            },
          })
            .then((res) => {
              ticketMessage(res.id);
            });
          return true;
        } catch (_) {
          return false;
        }
      },
    });
  };

  return diabledCluster;
};
