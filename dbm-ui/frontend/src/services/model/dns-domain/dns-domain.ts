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

export type DnsDomainMaintainType = 'self' | 'cluster';

/**
 * 域名服务的域名（列表行）
 */
export default class DnsDomain {
  bk_biz_id: number;
  bk_cloud_id: number;
  cluster_id: number | null;
  deletable: boolean;
  domain: string;
  editable: boolean;
  has_dns_manage: boolean;
  maintain_type: DnsDomainMaintainType;
  maintain_type_display: string;
  owners: string[];
  permission: {
    dns_manage: boolean;
  };
  remark: string;

  constructor(payload = {} as DnsDomain) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.cluster_id = payload.cluster_id;
    this.deletable = payload.deletable;
    this.domain = payload.domain;
    this.editable = payload.editable;
    this.has_dns_manage = payload.has_dns_manage;
    this.maintain_type = payload.maintain_type;
    this.maintain_type_display = payload.maintain_type_display;
    this.owners = payload.owners || [];
    this.permission = payload.permission || { dns_manage: false };
    this.remark = payload.remark;
  }

  // 自主维护：可在域名服务中编辑、删除；集群托管只读
  get isSelfMaintain() {
    return this.maintain_type === 'self';
  }
}
