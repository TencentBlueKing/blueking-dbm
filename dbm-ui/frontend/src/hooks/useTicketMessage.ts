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

export const useTicketMessage = () => {
  const { t } = useI18n();
  const router = useRouter();
  return (id: number) => {
    const route = router.resolve({
      name: 'SelfServiceMyTickets',
      query: {
        filterId: id,
      },
    });

    Message({
      message: h('p', {}, [
        t('任务提交成功_具体结果可前往'),
        h('a', {
          href: route.href,
          target: '_blank',
        }, ` "${t('我的服务单')}" `),
        t('查看'),
      ]),
      theme: 'success',
      delay: 6000,
      dismissable: false,
    });
  };
};
