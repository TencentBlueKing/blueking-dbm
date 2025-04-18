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

import type { HostInfo } from '@services/types';

import { Affinity } from '@common/const';

/**
 * 初始化表单数据
 * @returns formdata
 */
export const getInitFormdata = () => ({
  bk_biz_id: '',
  details: {
    bk_cloud_id: 0,
    city_code: '',
    db_app_abbr: '',
    db_version: '',
    disaster_tolerance_level: Affinity.MAX_EACH_ZONE_EQUAL, // 同 affinity
    group_id: '',
    ip_source: 'resource_pool',
    nodes: {
      influxdb: [] as HostInfo[],
    },
    port: 8080,
    resource_spec: {
      influxdb: {
        count: 1,
        spec_id: '',
      },
    },
    sub_zone_ids: [] as number[],
  },
  remark: '',
  ticket_type: 'INFLUXDB_APPLY',
});
