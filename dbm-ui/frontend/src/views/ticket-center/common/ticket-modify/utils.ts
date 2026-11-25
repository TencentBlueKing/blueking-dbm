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

import type { TicketModifyChangeItem } from '@services/model/ticket/modify-record';

import { messageError } from '@utils';

import { t } from '@locales/index';

import { type RequestErrorBody, TICKET_MODIFY_ERROR_CODE } from './constants';

export type Snapshot = Record<string, unknown>;

export interface DiffOptions {
  // 字段路径 → 展示值，可按 path 取同一份快照里的相邻字段（如 spec_id 展示 spec_name）
  formatters?: Record<string, (value: unknown, snapshot: Snapshot, path: string) => string>;
  // 派生只读字段与后端注入字段，不参与对比
  ignorePaths?: string[];
  // 字段路径 → 变更项名称，未登记的路径展示路径本身
  labels?: Record<string, string>;
  // 只在一侧出现也要对比的嵌套字段路径（如可选角色 resource_spec.*），缺失的一侧视为空，其下字段逐个列出
  unionPaths?: string[];
}

// 与改单记录的 change_details 同一结构：提交时算出的变更项原样存储、原样展示
export type DiffItem = TicketModifyChangeItem;

// 后端在 details 中注入的字段，提交体里没有；以及各申请页 formData 顶层残留的表单状态字段，不参与对比
const COMMON_IGNORE_PATHS = [
  '__ticket_detail__',
  'clusters',
  'specs',
  'sub_zone_ids',
  'sub_zone_names',
  'zone_names',
  'bk_cloud_zone_list',
  // location_spec 内的地域与顶层 bk_cloud_region 同值冗余，只按顶层计
  'resource_spec.*.location_spec.bk_cloud_region',
];

// 顶层字段公共中文名：各类型 DIFF 未单独登记 label 时兜底
const COMMON_LABELS: Record<string, string> = {
  bk_cloud_region: t('地域'),
  tags: t('集群标签'),
};

// 只在一侧出现也要对比：location_spec.bk_cloud_zone_list 随机时不传；
// disaster_tolerance_level / bk_cloud_region 部分单据 details 顶层未存，改动要能比出来；
// tags 是标签新能力，存量单据 details 顶层没有该字段，改单加标签要能比出来
const COMMON_UNION_PATHS = [
  'resource_spec.*.location_spec.bk_cloud_zone_list',
  'disaster_tolerance_level',
  'bk_cloud_region',
  'tags',
];

// 路径与登记项逐段比较，登记项中的 * 匹配任意一段
const isPathMatch = (path: string, pattern: string) => {
  const pathSegments = path.split('.');
  const patternSegments = pattern.split('.');
  return (
    pathSegments.length === patternSegments.length &&
    patternSegments.every((segment, index) => segment === '*' || segment === pathSegments[index])
  );
};

// 精确路径优先，其次是带 * 的登记项
const findByPath = <T>(map: Record<string, T> | undefined, path: string) => {
  if (!map) {
    return undefined;
  }
  if (path in map) {
    return map[path];
  }
  const pattern = Object.keys(map).find((key) => key.includes('*') && isPathMatch(path, key));
  return pattern ? map[pattern] : undefined;
};

const isEmptyValue = (value: unknown) =>
  value === undefined || value === null || value === '' || (Array.isArray(value) && value.length === 0);

export const formatValue = (value: unknown): string => {
  if (value === undefined || value === null || value === '') {
    return '--';
  }
  if (Array.isArray(value)) {
    return value.length ? value.map((item) => formatValue(item)).join(', ') : '--';
  }
  if (_.isPlainObject(value)) {
    return JSON.stringify(value);
  }
  return String(value);
};

/**
 * 集群标签（单键对象数组，如 [{"env": "prod"}]）转 "key: value" 逗号串；
 * 空返回空串，由调用方决定空值占位
 */
export const formatClusterTags = (value: unknown): string =>
  (Array.isArray(value) ? value : [])
    .map((item) => {
      const [key, val] = Object.entries(item as Record<string, string>)[0] ?? [];
      return val === undefined ? (key ?? '') : `${key}: ${val}`;
    })
    .filter(Boolean)
    .join(', ');

const CLUSTER_TAG_ROW_PATHS = ['domains', 'replica_sets', 'infos'];

/**
 * 域名表类单据把集群标签存在每行上，改单对比时提到顶层单独算「集群标签」变更项，
 * 避免拼进「域名设置」里；不修改原始 details。
 */
export const normalizeClusterTagsForDiff = (details: unknown) => {
  if (!_.isPlainObject(details)) {
    return details;
  }
  const result = _.cloneDeep(details as Record<string, unknown>);
  const tags: Record<string, string>[] = [];
  CLUSTER_TAG_ROW_PATHS.forEach((path) => {
    const rows = result[path];
    if (!Array.isArray(rows)) {
      return;
    }
    rows.forEach((row) => {
      if (_.isPlainObject(row) && Array.isArray(row.tags)) {
        tags.push(...(row.tags as Record<string, string>[]));
        // eslint-disable-next-line no-param-reassign
        delete row.tags;
      }
    });
  });
  if (tags.length && !result.tags) {
    result.tags = tags;
  }
  return result;
};

/**
 * 对比两份单据 details，返回有差异的字段
 * 对象逐层下钻；数组整体比较，有差异计 1 项；两侧都为空（undefined / null / '' / []）视为相同
 * 只对比两侧都有的字段：后端保存时会剔除提交体里未声明的字段（如 db_app_abbr），
 * 并补充展示用字段（如 bk_cloud_name），只在一侧出现的字段不是用户的改动；unionPaths 登记的嵌套字段除外
 * 改单提交时用它算出变更项，作为 change_details 随改单提交；详情页的变更对比直接展示提交时存下的结果
 */
export const diffDetails = (prev: unknown, next: unknown, options: DiffOptions = {}) => {
  const ignorePaths = [...COMMON_IGNORE_PATHS, ...(options.ignorePaths || [])];
  const unionPaths = [...COMMON_UNION_PATHS, ...(options.unionPaths || [])];
  const prevSnapshot = (prev || {}) as Snapshot;
  const nextSnapshot = (next || {}) as Snapshot;
  const result: DiffItem[] = [];

  // isOneSide：字段只在一侧出现（经 unionPaths 进入），缺失的一侧按空对象逐字段展开
  const walk = (prevValue: unknown, nextValue: unknown, path: string, isOneSide = false) => {
    if (ignorePaths.some((pattern) => isPathMatch(path, pattern))) {
      return;
    }
    if (isEmptyValue(prevValue) && isEmptyValue(nextValue)) {
      return;
    }
    const isPrevObject = _.isPlainObject(prevValue);
    const isNextObject = _.isPlainObject(nextValue);
    if (
      (isPrevObject && isNextObject) ||
      (isOneSide && ((isPrevObject && _.isNil(nextValue)) || (isNextObject && _.isNil(prevValue))))
    ) {
      const prevObject = (isPrevObject ? prevValue : {}) as Snapshot;
      const nextObject = (isNextObject ? nextValue : {}) as Snapshot;
      const prevKeys = Object.keys(prevObject);
      const nextKeys = Object.keys(nextObject);
      _.union(prevKeys, nextKeys).forEach((key) => {
        const childPath = `${path}.${key}`;
        const isShared = prevKeys.includes(key) && nextKeys.includes(key);
        if (isShared || isOneSide || unionPaths.some((pattern) => isPathMatch(childPath, pattern))) {
          walk(prevObject[key], nextObject[key], childPath, isOneSide || !isShared);
        }
      });
      return;
    }
    if (_.isEqual(prevValue, nextValue)) {
      return;
    }
    const formatter = findByPath(options.formatters, path);
    const prevText = formatter ? formatter(prevValue, prevSnapshot, path) : formatValue(prevValue);
    const nextText = formatter ? formatter(nextValue, nextSnapshot, path) : formatValue(nextValue);
    // 展示出来一样的不算改动：后端改单后会重算派生字段（如域名对象补全），原值相同但结构不同
    if (prevText === nextText) {
      return;
    }
    result.push({
      isList: Array.isArray(prevValue) || Array.isArray(nextValue),
      label: findByPath(options.labels, path) || COMMON_LABELS[path] || path,
      next: nextText,
      path,
      prev: prevText,
    });
  };

  // 顶层只比两侧都有的字段（后端会注入 / 剔除顶层字段）；unionPaths 登记的路径只在一侧出现也参与对比
  _.union(Object.keys(prevSnapshot), Object.keys(nextSnapshot)).forEach((key) => {
    const isShared = key in prevSnapshot && key in nextSnapshot;
    if (!isShared && !unionPaths.some((pattern) => isPathMatch(key, pattern))) {
      return;
    }
    walk(prevSnapshot[key], nextSnapshot[key], key, !isShared);
  });

  return result;
};

/**
 * 「通过 / 拒绝」请求的 payload：只接管内容版本冲突，其余错误码照常由请求层提示
 */
export const approvalRequestPayload = {
  catchErrorCodes: [TICKET_MODIFY_ERROR_CODE.CONTENT_CHANGED],
};

/**
 * 「通过 / 拒绝」的错误处理：版本冲突时提示单据已被提单人重新编辑
 * 表单校验失败等其它 reject 不提示，继续 reject 让确认气泡保持打开
 */
export const handleApprovalError = (error: unknown) => {
  if ((error as RequestErrorBody | undefined)?.code === TICKET_MODIFY_ERROR_CODE.CONTENT_CHANGED) {
    messageError(t('单据内容已被提单人重新编辑，请刷新后重新审批'));
  }
  return Promise.reject(error);
};
