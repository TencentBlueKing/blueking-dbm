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

import { AccountTypes } from '@common/const';

import configMap from '@views/db-manage/common/permission/components/mysql/config';

export const isSensitivePriv = (accountType: AccountTypes, priv: string) => {
  const dbOprationsMap: Record<string, string[]> = {
    [AccountTypes.MYSQL]: [
      ...configMap[AccountTypes.MYSQL].dbOperations.glob,
      ...configMap[AccountTypes.MYSQL].ddlSensitiveWords,
    ],
    [AccountTypes.TENDBCLUSTER]: configMap[AccountTypes.TENDBCLUSTER].dbOperations.glob,
  };

  const dbOprations = dbOprationsMap[accountType];
  return dbOprations.includes(priv);
};
