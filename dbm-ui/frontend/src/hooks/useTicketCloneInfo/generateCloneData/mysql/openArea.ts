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
import _ from 'lodash';

import type { MysqlOpenAreaDetails } from '@services/model/ticket/details/mysql';
import TicketModel from '@services/model/ticket/ticket';
import { getDetail } from '@services/source/openarea';

import { random } from '@utils';

// 解析器，根据范式提取变量映射关系
const parser = (pattern: string, input: string) => {
  const regexPattern = new RegExp(pattern.replace(/{(.+?)}/g, '(?<$1>.+)'));
  return input.match(regexPattern)?.groups || {};
};

// MySQL 开区
export async function generateMysqlOpenAreaCloneData(ticketData: TicketModel<MysqlOpenAreaDetails>) {
  const { details } = ticketData;
  // 获取模板详情
  const templateDetail = await getDetail({ id: details.config_id });

  const data = details.config_data.map((cur, index) => {
    // 集群信息
    const clusterInfo = details.clusters[cur.cluster_id];

    // 变量
    const vars = cur.execute_objects.reduce<Record<string, string>>((varAcc, varCur) => {
      const varItem = templateDetail.config_rules.reduce(
        (acc, cur) => ({
          ...acc,
          ...parser(cur.target_db_pattern, varCur.target_db),
        }),
        {},
      );
      return { ...varAcc, ...varItem };
    }, {});

    // 授权IP
    const authorizeIps: string[] = _.get(details, `rules_set[${index}].source_ips`, []);

    return {
      rowKey: random(),
      clusterData: {
        id: clusterInfo.id,
        master_domain: clusterInfo.immute_domain,
        bk_biz_id: clusterInfo.bk_biz_id,
        bk_cloud_id: clusterInfo.bk_cloud_id,
        bk_cloud_name: clusterInfo.bk_cloud_name,
      },
      vars,
      authorizeIps,
    };
  });

  return Promise.resolve({
    id: details.config_id,
    data,
  });
}
