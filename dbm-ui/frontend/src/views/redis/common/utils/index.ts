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

import { queryClustersInfo } from '@services/redis/toolbox';
import { getVersions } from '@services/versionFiles';

import { ClusterTypes } from '@common/const';

// 根据关键字查询集群信息
export const getClusterInfo = async (domain: string | string[]) => await queryClustersInfo({
  keywords: Array.isArray(domain) ? domain : [domain],
  role: 'proxy',
}).catch((e) => {
  console.error('queryClustersInfo error: ', e);
  return null;
});

// 获取 redis 版本信息
export const getRedisVersions = async () => {
  const arr = await getVersions({ query_key: ClusterTypes.TWEMPROXY_REDIS_INSTANCE })
    .catch((e) => {
      console.error('query redis version failed: ', e);
      return null;
    });
  if (arr) {
    return arr.map(item => ({
      id: item,
      name: item,
    }));
  }
  return null;
};


// 首字母大写
export const firstLetterToUpper = (str: string) => str.charAt(0).toUpperCase() + str.slice(1);
