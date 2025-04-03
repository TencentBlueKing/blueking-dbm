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

import FaultOrRecycleMachineModel from '@services/model/db-resource/FaultOrRecycleMachine';
import type { HostInfo } from '@services/types';

import { useSystemEnviron } from '@stores';

import { getBusinessHref } from '@utils';

export const useImportResourcePoolTooltip = (hostList?: Ref<(FaultOrRecycleMachineModel | HostInfo)[]>) => {
  const { t } = useI18n();
  const router = useRouter();
  const systemEnvironStore = useSystemEnviron();

  const taskHistoryListRoute = router.resolve({
    name: 'taskHistoryList',
    query: {
      ticket_type__in: 'RESOURCE_IMPORT',
    },
  });
  const taskHistoryListHref = getBusinessHref(taskHistoryListRoute.href, systemEnvironStore.urls.DBA_APP_BK_BIZ_ID);

  const tooltip = computed(() => {
    const content = {
      content: () => (
        <div>
          {t('提交后，将会进行主机初始化任务，具体的导入结果，可以通过“')}
          <a
            href={taskHistoryListHref}
            target='_blank'>
            {t('任务历史')}
          </a>
          {t('”查看')}
        </div>
      ),
      theme: 'light',
    };

    if (hostList?.value === undefined) {
      return content;
    }

    return hostList.value.length
      ? content
      : {
          content: t('请选择主机'),
          disabled: !!hostList.value.length,
        };
  });

  // 根据导入任务的数量决定跳转的页面
  const getImportTaskHref = (taskIds: string[]) => {
    const getRouteInfo = (taskIds: string[]) => {
      if (taskIds.length === 1) {
        return router.resolve({
          name: 'taskHistoryDetail',
          params: {
            root_id: taskIds[0],
          },
        });
      }
      return router.resolve({
        name: 'taskHistoryList',
        query: {
          ticket_type__in: 'RESOURCE_IMPORT',
        },
      });
    };

    const routeInfo = getRouteInfo(taskIds);
    return getBusinessHref(routeInfo.href, systemEnvironStore.urls.DBA_APP_BK_BIZ_ID);
  };

  const successMessage = (taskIds: string[]) => {
    const routeInfoHref = getImportTaskHref(taskIds);

    Message({
      delay: 6000,
      dismissable: false,
      message: h('p', {}, [
        t('任务提交成功_具体结果可前往'),
        h(
          'a',
          {
            href: routeInfoHref,
            target: '_blank',
          },
          ` "${t('任务')}" `,
        ),
        t('查看'),
      ]),
      theme: 'success',
    });
  };

  return {
    getImportTaskHref,
    successMessage,
    taskHistoryListHref,
    tooltip,
  };
};
