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

import DnsDomainModel, { type DnsDomainMaintainType } from '@services/model/dns-domain/dns-domain';
import DnsDomainAuditModel, { type DnsDomainAuditAction } from '@services/model/dns-domain/dns-domain-audit';

import http, { type IRequestPayload } from '../http';

const path = '/apis/dns_domain';

export interface DnsDomainDetail {
  bk_biz_id: number;
  bk_cloud_id: number;
  cluster_id: number | null;
  domain: string;
  ips: string[];
  maintain_type: DnsDomainMaintainType;
  maintain_type_display: string;
  owners: string[];
  readonly_reason: string;
  remark: string;
}

export type DnsDomainAuditScope = 'domain' | 'global';

interface AuditParams {
  action?: DnsDomainAuditAction | string;
  domain?: string;
  keyword?: string;
  limit?: number;
  offset?: number;
  operator?: string;
  scope: DnsDomainAuditScope;
}

/**
 * 域名列表
 */
export const getDnsDomainList = (
  params: {
    domain?: string;
    limit?: number;
    maintain_type?: DnsDomainMaintainType | string;
    mine?: boolean;
    offset?: number;
    owner?: string;
  },
  payload = {} as IRequestPayload,
) =>
  http
    .get<{
      can_create: boolean;
      can_view_global_audit: boolean;
      count: number;
      permission: {
        dns_audit_view: boolean;
        dns_domain_create: boolean;
      };
      results: DnsDomainModel[];
    }>(`${path}/domains/`, params, payload)
    .then((data) => ({
      ...data,
      results: data.results.map((item) => new DnsDomainModel(item)),
    }));

/**
 * 域名详情
 */
export const getDnsDomainDetail = (params: { domain: string }) =>
  http.get<DnsDomainDetail>(`${path}/domains/detail/`, params);

/**
 * 新建自主维护域名
 */
export const createDnsDomain = (params: { domain: string; ips: string[]; owners: string[]; remark?: string }) =>
  http.post<DnsDomainDetail>(`${path}/domains/create/`, params);

/**
 * 保存自主维护域名，ips 为保存后的完整集合
 */
export const updateDnsDomain = (params: { domain: string; ips: string[]; owners: string[]; remark?: string }) =>
  http.post<DnsDomainDetail>(`${path}/domains/update/`, params);

/**
 * 删除自主维护域名
 */
export const deleteDnsDomain = (params: { confirm_domain: string; domain: string }) =>
  http.post<{ domain: string }>(`${path}/domains/delete/`, params);

/**
 * 操作日志（本域 / 全局）
 */
export const getDnsDomainAudits = (params: AuditParams, payload = {} as IRequestPayload) =>
  http
    .get<{
      count: number;
      results: DnsDomainAuditModel[];
    }>(`${path}/audits/`, params, payload)
    .then((data) => ({
      ...data,
      results: data.results.map((item) => new DnsDomainAuditModel(item)),
    }));

/**
 * 导出操作日志，文件名由后端决定（含日期），不追加时间戳
 */
export const exportDnsDomainAudits = (params: Omit<AuditParams, 'limit' | 'offset'>) =>
  http.get<string>(`${path}/audits/export/`, params, {
    keepFileName: true,
    responseType: 'blob',
  });
