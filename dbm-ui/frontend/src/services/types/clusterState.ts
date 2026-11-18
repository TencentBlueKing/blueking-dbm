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
 * 集群状态框架：列表每行 states 中的单个字段取值
 */
export interface ClusterStateValue {
  // 下钻摘要，一期不使用
  detail: unknown;
  // 展示文本，后端按 value_type 生成
  display: string;
  updated_at: string | null;
  // 原始取值，null 表示未采集
  value: unknown;
}

/**
 * 集群状态框架：字段定义
 */
export interface ClusterStateField {
  // 可选值：接口实际返回 { value, label }，文档写的是 [value, label]
  choices: ({ label: string; value: string | number | boolean } | [string | number | boolean, string])[];
  default_value: unknown;
  drilldown_type: string | null;
  filterable: boolean;
  help_text: string;
  key: string;
  name: string;
  source: string;
  value_type: string;
  writable: boolean;
}

/**
 * 集群状态框架：某集群类型的字段定义与默认展示列
 */
export interface ClusterStateSchema {
  cluster_type: string;
  // 默认展示列，顺序即展示顺序
  display_fields: string[];
  fields: ClusterStateField[];
}
