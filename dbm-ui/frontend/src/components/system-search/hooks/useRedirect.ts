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

import { clusterTypeInfos } from '@common/const';

import { getBusinessHref } from '@utils';

export const useRedirect = () => {
  const router = useRouter();

  const routerNameMap = Object.fromEntries(
    Object.values(clusterTypeInfos).map((item) => [item.id, item.listRouteName]),
  );

  return (clusterType: string, queryParams: Record<string, any>, bizId: number) => {
    if (!routerNameMap[clusterType]) {
      return;
    }

    const { href } = router.resolve({
      name: routerNameMap[clusterType],
      query: queryParams,
    });
    // 业务 id 为空时保持原地址，不替换成当前业务
    window.open(bizId ? getBusinessHref(href, bizId) : href);
  };
};
