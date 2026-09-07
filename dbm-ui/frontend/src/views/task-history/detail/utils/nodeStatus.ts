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

import { t } from '@locales/index';

/** 节点的展示状态，与接口下发的 status 不是一一对应：待继续、已跳过都由额外字段推出来 */
export type NodeDisplayStatus = 'CREATED' | 'FAILED' | 'FINISHED' | 'READY' | 'RUNNING' | 'SKIPPED' | 'TODO';

/** 判定只需要这几个字段，画布节点、搜索树节点、节点详情拿到的对象都满足 */
interface StatusSource {
  error_ignorable?: boolean;
  skip?: boolean;
  status?: string;
  todoId?: number;
}

/**
 * 节点展示状态的唯一判定入口。
 *
 * 画布卡片、搜索树、节点详情、执行日志此前各写了一遍，规则必须完全一致，否则同一个节点
 * 在不同位置会显示成不同状态。优先级：失败 > 待执行 > 准备中 > 待继续 > 执行中 > 已跳过 > 执行成功
 */
export const getNodeDisplayStatus = (node: StatusSource): NodeDisplayStatus => {
  if (node.status === 'FAILED' || node.status === 'REVOKED') {
    return 'FAILED';
  }
  // 还没开始执行的节点不可能带待继续或跳过标记，先短路掉，避免脏数据把它判成别的状态
  if (!node.status || node.status === 'CREATED') {
    return 'CREATED';
  }
  // 已调度但还没真正跑起来，同样不会带待继续或跳过标记
  if (node.status === 'READY') {
    return 'READY';
  }
  if (node.todoId) {
    return 'TODO';
  }
  if (node.status === 'RUNNING') {
    return 'RUNNING';
  }
  // skip 是人工跳过，error_ignorable 是失败自动跳过，两者都展示为已跳过
  if (node.status === 'SKIPPED' || node.skip || node.error_ignorable) {
    return 'SKIPPED';
  }
  return node.status === 'FINISHED' ? 'FINISHED' : 'CREATED';
};

/** 搜索树筛选与状态计数的口径，与筛选下拉的选项一一对应 */
export type NodeFilterStatus = Exclude<NodeDisplayStatus, 'SKIPPED'>;

/**
 * 筛选与计数时已跳过仍算执行成功。
 * 筛选下拉里没有「已跳过」这一项，单独拆出来会让跳过的节点在任何筛选下都消失
 */
export const getNodeFilterStatus = (node: StatusSource): NodeFilterStatus => {
  const status = getNodeDisplayStatus(node);
  return status === 'SKIPPED' ? 'FINISHED' : status;
};

interface StatusMeta {
  /** 画布卡片左侧色块与右上角状态图标的底色 */
  canvasFill: string;
  /** 画布右上角状态图标 hover 时的底色，待执行的节点不画图标 */
  canvasHoverFill?: string;
  /** 画布卡片的边框色 */
  canvasStroke: string;
  /** 主色：搜索树节点图标、节点详情、画布图例 */
  color: string;
  /** 搜索树筛选下拉里小圆点的底色，执行中、准备中画的是旋转图标而不是圆点 */
  dotFill?: string;
  text: string;
}

/** 准备中的视觉与执行中完全一致，只有文案不同 */
const runningStatusMeta: StatusMeta = {
  canvasFill: '#3A84FF',
  canvasHoverFill: '#1768EF',
  canvasStroke: '#3A84FF',
  color: '#3A84FF',
  text: t('执行中'),
};

/**
 * 状态的展示口径。
 *
 * 注意 color 与 canvasFill 是两组值：前者是全站通用的状态色，后者是画布上的图标底色，
 * 历史上就不一样（如执行成功 #2CAF5E / #3DC2A6）。这里先并到一张表里让差异可见，
 * 要不要统一成一组由设计定，改一行即可
 */
export const NODE_STATUS_META: Record<NodeDisplayStatus, StatusMeta> = {
  CREATED: {
    canvasFill: '#C4C6CC',
    canvasStroke: '#F0F1F5',
    color: '#C4C6CC',
    dotFill: '#F0F1F5',
    text: t('待执行'),
  },
  FAILED: {
    canvasFill: '#FF4D4D',
    canvasHoverFill: '#FF0000',
    canvasStroke: '#FF4D4D',
    color: '#EA3636',
    dotFill: '#FFDDDD',
    text: t('执行失败'),
  },
  FINISHED: {
    canvasFill: '#3DC2A6',
    canvasHoverFill: '#319B85',
    canvasStroke: '#A1E3BA',
    color: '#2CAF5E',
    dotFill: '#CBF0DA',
    text: t('执行成功'),
  },
  READY: {
    ...runningStatusMeta,
    text: t('准备中'),
  },
  RUNNING: runningStatusMeta,
  SKIPPED: {
    canvasFill: '#7FBB44',
    canvasHoverFill: '#6CA633',
    canvasStroke: '#7FBB44',
    color: '#8EBF76',
    text: t('已跳过'),
  },
  TODO: {
    canvasFill: '#F59500',
    canvasHoverFill: '#E38B02',
    canvasStroke: '#F59500',
    color: '#F59500',
    dotFill: '#FCE5C0',
    text: t('待继续'),
  },
};
