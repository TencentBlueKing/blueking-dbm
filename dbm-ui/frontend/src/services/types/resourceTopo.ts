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

/**
 * 集群详情拓扑图数据
 */
export interface ResourceTopo {
  foreign_relations: {
    access_from: [];
    access_to: [];
    rep_from: [];
    rep_to: [];
  };
  groups: {
    children_id: string[];
    group_name: string;
    node_id: string;
  }[];
  lines: {
    label: string;
    label_name: string;
    source: string;
    source_type: string;
    target: string;
    target_type: string;
  }[];
  node_id: string;
  nodes: {
    node_id: string;
    node_type: string;
    status?: string;
    url: string;
  }[];
}
