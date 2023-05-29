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

export interface IPagination {
  current: number,
  count: number,
  limit: number,
  'limit-list': number[],
  getFetchParams: () => ({ limit: number, offset: number })
}

/**
 * 根据初始屏幕高度大小返回分页配置信息
 */
const limit = window.innerHeight > 750 ? 20 : 10;
export const useDefaultPagination = () => ({
  current: 1,
  count: 0,
  limit,
  'limit-list': [limit, 50, 100, 500],
  getFetchParams() {
    return {
      limit: this.limit,
      offset: this.limit * (this.current - 1),
    };
  },
});
