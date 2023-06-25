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

import type { HostDetails } from '@services/types/ip';

/**
 * 初始化表单数据
 * @returns formdata
 */
export const getInitFormdata = () => ({
  bk_biz_id: '',
  ticket_type: 'INFLUXDB_APPLY',
  remark: '',
  details: {
    bk_cloud_id: '',
    ip_source: 'resource_pool',
    db_app_abbr: '',
    city_code: '',
    db_version: '',
    port: 8080,
    group_id: '',
    nodes: {
      influxdb: [] as HostDetails[],
    },
    resource_spec: {
      influxdb: {
        spec_id: '',
        count: 1,
      },
    },
  },
});
