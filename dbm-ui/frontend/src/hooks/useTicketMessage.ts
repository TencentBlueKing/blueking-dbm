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

import { Message } from 'bkui-vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';

import { useSystemEnviron } from '@stores';

import { getBusinessHref } from '@utils';

export const useTicketMessage = (
  params: {
    isCurrentBiz?: boolean;
  } = {},
) => {
  const { t } = useI18n();
  const router = useRouter();
  const systemEnvironStore = useSystemEnviron();

  return (ticketIds: number | number[]) => {
    const ticketRoute = {
      name: 'bizTicketManage',
    };
    const isArray = Array.isArray(ticketIds);
    const ids = isArray ? ticketIds : [ticketIds];
    const count = ids.length;

    if (count === 1) {
      Object.assign(ticketRoute, {
        params: {
          ticketId: ids[0],
        },
      });
    } else {
      Object.assign(ticketRoute, {
        query: {
          ids: ids.join(','),
        },
      });
    }

    const routeInfo = router.resolve(ticketRoute);
    const routeInfoHref = params.isCurrentBiz
      ? routeInfo.href
      : getBusinessHref(routeInfo.href, systemEnvironStore.urls.RESOURCE_INDEPENDENT_BIZ);

    const messageText = count === 1 ? t('操作提交成功') : t('操作提交成功，已生成 {n} 个单据', { n: count });

    Message({
      delay: 6000,
      dismissable: false,
      message: h('div', { style: 'width: 100%; display: flex; justify-content: space-between;' }, [
        h('span', {}, messageText),
        h(
          'a',
          {
            href: routeInfoHref,
            target: '_blank',
          },
          t('查看详情'),
        ),
      ]),
      theme: 'success',
    });
  };
};
