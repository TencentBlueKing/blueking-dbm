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

import http from '../http';

/**
 * 查询 DBA 人员列表
 */
export function getReportShare(params: { record_id: string }) {
  return http.get<{
    ai_agent: string;
    bk_biz_id: number;
    cluster_domain: string;
    content: string;
    create_at: string;
    creator: string;
    format: 'markdown' | 'html';
    report_id: string;
    summary: string;
    title: string;
    update_at: string;
  }>(`/db_report/share/${params.record_id}/`);
}
