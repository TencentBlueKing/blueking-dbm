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

// 后端在 details 中注入的字段，提交体里没有
const COMMON_IGNORE_PATHS = ['__ticket_detail__', 'clusters', 'specs'];

// 随机园区时 location_spec 不带 sub_zone_ids，在「指定园区」与「随机」之间切换要能比出来
const COMMON_UNION_PATHS = ['resource_spec.*.location_spec.sub_zone_ids'];

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
      label: findByPath(options.labels, path) || path,
      next: nextText,
      path,
      prev: prevText,
    });
  };

  _.intersection(Object.keys(prevSnapshot), Object.keys(nextSnapshot)).forEach((key) => {
    walk(prevSnapshot[key], nextSnapshot[key], key);
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
