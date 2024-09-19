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
import { InfoBox, Message } from 'bkui-vue';
import { useI18n } from 'vue-i18n';
import { useRequest } from 'vue-request';

import { deleteMongodbAccount } from '@services/source/mongodbPermissionAccount';

import { useGlobalBizs } from '@stores';

import { AccountTypes } from '@common/const';

export const useDeleteAccount = () => {
  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const { run } = useRequest(deleteMongodbAccount, {
    manual: true,
  });

  const deleteAccountReq = (user: string, accountId: number, callback: () => void) => {
    InfoBox({
      type: 'warning',
      title: t('确认删除该账号'),
      content: t('即将删除账号xx_删除后将不能恢复', { name: user }),
      quickClose: true,
      onConfirm: async () => {
        try {
          run({
            bizId: currentBizId,
            account_id: accountId,
            account_type: AccountTypes.MONGODB,
          });

          Message({
            message: t('成功删除账号'),
            theme: 'success',
          });

          callback();

          return true;
        } catch (_) {
          return false;
        }
      },
    });
  };

  return { deleteAccountReq };
};
