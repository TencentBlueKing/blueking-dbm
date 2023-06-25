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
  remark: '',
  ticket_type: 'PULSAR_APPLY',
  details: {
    username: '',
    password: '',
    ip_source: 'resource_pool',
    db_version: '',
    bk_cloud_id: '',
    retention_hours: 1,
    replication_num: 2,
    ack_quorum: 1,
    port: 9200,
    partition_num: 1,
    cluster_name: '',
    cluster_alias: '',
    city_code: '',
    db_app_abbr: '',
    nodes: {
      zookeeper: [] as HostDetails[],
      broker: [] as HostDetails[],
      bookkeeper: [] as HostDetails[],
    },
    resource_spec: {
      zookeeper: {
        spec_id: '',
        count: 3,
      },
      broker: {
        spec_id: '',
        count: 1,
      },
      bookkeeper: {
        spec_id: '',
        count: 2,
      },
    },
  },
});
