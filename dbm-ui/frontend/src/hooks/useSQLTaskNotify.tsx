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

import { Notify } from 'bkui-vue';
import { useI18n } from 'vue-i18n';

import type UserSemanticTaskModel from '@services/model/sql-import/user-semantic-task';
import {
  getUserSemanticTasks,
} from '@services/sqlImport';

import { useTimeoutPoll } from '@vueuse/core';

export const useSQLTaskNotify = () => {
  const { t } = useI18n();
  const router = useRouter();

  const handleGoTaskLog = (taskData: UserSemanticTaskModel) => {
    router.push({
      name: 'MySQLExecute',
      params: {
        step: 'log',
        bizId: taskData.bk_biz_id,
      },
      query: {
        rootId: taskData.root_id,
        nodeId: taskData.node_id,
      },
    });
  };

  const fetchData = () => {
    getUserSemanticTasks({
      bk_biz_id: 0,
    }).then((data) => {
      for (const item of data) {
        if (item.is_alter) {
          const text = item.isSucceeded ? t('成功') : t('失败');
          Notify({
            position: 'top-right',
            theme: item.isSucceeded ? 'success' : 'error',
            title: t('SQL变更执行'),
            delay: 10000,
            message: () => (
              <>
                <p class="mb-16">{t('xx的模拟任务执行_Text', { text, name: item.created_at })}</p>
                <a href="javascript:" onClick={handleGoTaskLog.bind(null, item)}>{t('查看详情')}</a>
              </>
            ),
          });
        }
      }
    });
  };

  const {
    pause,
  } = useTimeoutPoll(fetchData, 10000, { immediate: true });

  onBeforeUnmount(() => {
    pause();
  });
};
