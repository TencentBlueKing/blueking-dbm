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

import { getUserList } from '@services/source/user';

import { ipv4 } from '@common/regex';

// 完整域名后缀，创建后固定
export const DOMAIN_SUFFIX = '.db';

// 每段为小写字母、数字、连字符，首尾为字母或数字，单段 ≤63
const domainLabelRegex = /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/;

/**
 * 校验完整域名：以 .db 结尾、总长 ≤253、每段合法
 */
export const isValidDomain = (domain: string) => {
  if (!domain.endsWith(DOMAIN_SUFFIX) || domain.length > 253) {
    return false;
  }
  const labels = domain.split('.');
  // 至少有一段前缀，如 api.db
  return labels.length > 1 && labels.every((label) => domainLabelRegex.test(label));
};

/**
 * 校验 IP 集合：每个都是不带端口的 IPv4
 */
export const isValidIpList = (ips: string[]) => ips.every((ip) => ipv4.test(ip));

/**
 * 搜索栏的人员远程候选（负责人、操作人共用）
 */
export const searchUserRemoteMethod = (params: { defaultValue?: string; keyword?: string }) => {
  const requestParams = {};
  if (params.defaultValue) {
    Object.assign(requestParams, { exact_lookups: params.defaultValue });
  }
  if (params.keyword) {
    Object.assign(requestParams, { fuzzy_lookups: params.keyword });
  }
  return getUserList(requestParams).then((data) =>
    data.results.map((item) => ({
      label: `${item.username} (${item.display_name})`,
      value: item.username,
    })),
  );
};
