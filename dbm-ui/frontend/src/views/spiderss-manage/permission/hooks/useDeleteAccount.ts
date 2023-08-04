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

import { deleteAccount } from '@services/spider/permission';

import { useInfoWithIcon } from '@hooks';

import { AccountTypes } from '@common/const';

export const useDeleteAccount = () => {
  const { t } = useI18n();

  const deleteAccountReq = (user: string, accountId: number, callback: any) => {
    useInfoWithIcon({
      type: 'warnning',
      title: t('确认删除该账号'),
      content: t('即将删除账号xx_删除后将不能恢复', { name: user }),
      props: {
        quickClose: true,
      },
      onConfirm: async () => {
        try {
          await deleteAccount({
            account_id: accountId,
            account_type: AccountTypes.TENDBCLUSTER,
          });

          Message({
            message: t('成功删除账号'),
            theme: 'success',
            delay: 1500,
          });

          callback();

          return true;
        } catch (_) {
          return false;
        }
      },
    });
  };

  return {
    deleteAccountReq,
  };
};
