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
import { useRequest } from 'vue-request';

import { getClusterStateSchema } from '@services/source/clusterState';
import type { ClusterStateField, ClusterStateSchema, ClusterStateValue } from '@services/types';

import { ClusterTypes } from '@common/const';

export interface ClusterStateFilterField {
  // 取值统一为字符串，便于搜索栏逗号拼接
  choices: {
    label: string;
    value: string;
  }[];
  key: string;
  name: string;
}

/**
 * 接入「运行概况」的集群类型，列表列、详情分组、搜索条件统一按此判断
 */
export const clusterStateSupportedTypes: ClusterTypes[] = [
  ClusterTypes.TENDBHA,
  ClusterTypes.TENDBSINGLE,
  ClusterTypes.TENDBCLUSTER,
];

/**
 * 状态字段取值对应的静态状态点主题：正常绿、异常红、临时信息蓝
 */
export const clusterStateStatusThemeMap: Record<string, string> = {
  abnormal: 'danger',
  normal: 'success',
  temporary: 'primary',
};

/**
 * 取字段展示文本，缺失或未采集时返回 --
 */
export const getClusterStateDisplay = (states: Record<string, ClusterStateValue> | undefined, key: string) => {
  const state = states?.[key];
  if (!state || state.value === null || state.value === undefined || state.display === '') {
    return '--';
  }
  return state.display;
};

// 后端过滤参数前缀：state__{key}=v1,v2
const CLUSTER_STATE_FILTER_PREFIX = 'state__';

/**
 * 「运行概况」筛选值编码：state__{key}#{value}
 * DbQuickSearch 对 multiple-cascader 按 # 拆分，最终输出 state__{key}=v1,v2
 */
export const encodeClusterStateFilterValue = (key: string, value: string) =>
  `${CLUSTER_STATE_FILTER_PREFIX}${key}#${value}`;

/**
 * 从编码值解析字段 key
 */
export const decodeClusterStateFilterKey = (encodedValue: string | number) =>
  String(encodedValue).split('#')[0].replace(CLUSTER_STATE_FILTER_PREFIX, '');

/**
 * 把可筛选字段转成搜索栏级联候选：父级为字段，子级为编码后的取值
 */
export const getClusterStateFilterCascaderList = (fields: ClusterStateFilterField[]) =>
  fields.map((field) => ({
    children: field.choices.map((choice) => ({
      label: choice.label,
      value: encodeClusterStateFilterValue(field.key, choice.value),
    })),
    label: field.name,
    value: `${CLUSTER_STATE_FILTER_PREFIX}${field.key}`,
  }));

/**
 * 回显文本：按字段分组，「字段名 ： 值1、值2」，多个字段以「；」分隔
 */
export const formatClusterStateFilterText = (
  values: { label: string; value: string | number }[],
  fieldNameMap: Record<string, string>,
) => {
  const groupMap = _.groupBy(values, (item) => decodeClusterStateFilterKey(item.value));
  return Object.entries(groupMap)
    .map(([key, items]) => `${fieldNameMap[key] || key} ： ${items.map((item) => item.label).join('、')}`)
    .join('；');
};

/**
 * 不作为筛选选项的取值
 * phase 的 destroy 只用于单据校验，不会写入集群（后端 2026-11-17 需求备注）
 */
const excludeFilterValueMap: Record<string, string[]> = {
  phase: ['destroy'],
};

/**
 * 按 display_fields 的顺序取字段定义，fields 中未声明的 key 直接忽略
 */
export const getClusterStateDisplayFields = (schema?: ClusterStateSchema) => {
  if (!schema) {
    return [];
  }
  const fieldMap = _.keyBy(schema.fields, 'key');
  return schema.display_fields.reduce<ClusterStateField[]>((result, key) => {
    if (fieldMap[key]) {
      result.push(fieldMap[key]);
    }
    return result;
  }, []);
};

/**
 * 统一 choices 单项格式：接口实际返回 { value, label }，文档写的是 [value, label]，两种都兼容
 */
const normalizeChoice = (choice: ClusterStateField['choices'][number]) => {
  if (Array.isArray(choice)) {
    return {
      label: String(choice[1] ?? choice[0]),
      value: String(choice[0]),
    };
  }
  return {
    label: String(choice.label ?? choice.value),
    value: String(choice.value),
  };
};

/**
 * 展示字段中可过滤且有固定取值的字段，作为「运行概况」筛选项
 */
export const getClusterStateFilterFields = (schema?: ClusterStateSchema) =>
  getClusterStateDisplayFields(schema).reduce<ClusterStateFilterField[]>((result, field) => {
    if (!field.filterable) {
      return result;
    }
    const excludeValues = excludeFilterValueMap[field.key] || [];
    const choices = (field.choices || []).map(normalizeChoice).filter((item) => !excludeValues.includes(item.value));
    if (choices.length > 0) {
      result.push({
        choices,
        key: field.key,
        name: field.name,
      });
    }
    return result;
  }, []);

/**
 * 按集群类型获取「运行概况」字段定义（接口带缓存，多处调用只请求一次）
 */
export const useClusterStateSchema = (clusterType: ClusterTypes) => {
  const { data, loading } = useRequest(getClusterStateSchema, {
    defaultParams: [
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        cluster_type: clusterType,
      },
    ],
  });

  const displayFields = computed(() => getClusterStateDisplayFields(data.value));
  const filterFields = computed(() => getClusterStateFilterFields(data.value));

  return {
    displayFields,
    filterFields,
    loading,
  };
};
