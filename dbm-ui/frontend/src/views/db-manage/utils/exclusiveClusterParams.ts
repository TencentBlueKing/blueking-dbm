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
import { isExclusiveClusterType } from '@common/const';

/**
 * 集群资源查询的独占集群参数
 * 仅白名单内的集群类型才需要透传 isPublic / bkBizId，`is_public` 缺失时按共享集群兜底；
 * 非白名单集群类型返回空对象，保持既有请求不变
 */
export const getExclusiveClusterParams = (cluster: {
  bk_biz_id?: number;
  cluster_type?: string;
  is_public?: boolean;
}): {
  bkBizId?: number;
  isPublic?: boolean;
} => {
  if (!isExclusiveClusterType(cluster.cluster_type)) {
    return {};
  }

  return {
    bkBizId: cluster.bk_biz_id,
    isPublic: cluster.is_public !== false,
  };
};
