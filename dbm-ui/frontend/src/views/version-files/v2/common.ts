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

import { DBTypes } from '@common/const';

/** 中文字符，标识类名称不允许出现 */
export const CHINESE_CHAR_REG = /[\u4e00-\u9fa5]/;

/** 标识类名称（发行版名、系列名、版本名、包类型标识）只允许字母、数字、连字符、下划线、点号 */
export const IDENTIFIER_NAME_REG = /^[A-Za-z0-9_.-]+$/;

/**
 * mysql 的 mysql 包类型是唯一支持多个发行版的场景，
 * 其余 DB 类型 / 包类型下只有一个隐式发行版，不展示左侧发行版列表
 */
export const isPureMysqlPkgType = (dbType: string, pkgType: string) => dbType === DBTypes.MYSQL && pkgType === 'mysql';

/** 版本阶段，按从早到晚排列，表格 tag、编辑表单、搜索栏候选项都由此派生 */
export const versionStageList: { label: string; theme: 'danger' | 'warning' | 'info' | 'success'; value: string }[] = [
  {
    label: 'Alpha',
    theme: 'danger',
    value: 'alpha',
  },
  {
    label: 'Beta',
    theme: 'warning',
    value: 'beta',
  },
  {
    label: 'RC',
    theme: 'info',
    value: 'rc',
  },
  {
    label: 'Release',
    theme: 'success',
    value: 'release',
  },
];

/** 按阶段值索引的版本阶段 */
export const versionStageMap = versionStageList.reduce<Record<string, (typeof versionStageList)[number]>>(
  (result, item) => Object.assign(result, { [item.value]: item }),
  {},
);
