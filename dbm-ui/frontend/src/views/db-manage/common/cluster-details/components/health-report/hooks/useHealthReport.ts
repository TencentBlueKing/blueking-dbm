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

import dayjs from 'dayjs';
import _ from 'lodash';

import { getClusterHealthReport, getReportShare } from '@services/source/dbReport';

/**
 * 报告内容区状态
 * report：有报告；empty：已接入但从未生成；noReport：该日无报告；unsupported：未接入或无法定位集群
 */
export type HealthReportStatus = 'report' | 'empty' | 'noReport' | 'unsupported';

/**
 * 解析 URL 中的数据日期，不是合法的 YYYY-MM-DD 时返回空字符串（按不带日期请求最新一份）
 * 项目未加载 dayjs customParseFormat 插件，用格式化回校排除 2026-13-45 这类值
 */
export const parseReportDate = (value: unknown) => {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return '';
  }
  return dayjs(value).format('YYYY-MM-DD') === value ? value : '';
};

export const useHealthReport = () => {
  const loading = ref(false);
  const status = ref<HealthReportStatus | ''>('');
  // 升序排列的有报告日期
  const availableDates = ref<string[]>([]);
  // 当前打开的数据日期，未带日期请求时为最新一天
  const currentDate = ref('');
  const reportToTime = ref('');
  const content = ref('');

  const latestDate = computed(() => _.last(availableDates.value) || '');

  // 换期过快时丢弃过期请求的结果
  let requestId = 0;

  const fetchReport = async (params: ServiceParameters<typeof getClusterHealthReport>) => {
    requestId += 1;
    const currentRequestId = requestId;
    loading.value = true;
    try {
      const data = await getClusterHealthReport(params);
      if (currentRequestId !== requestId) {
        return;
      }
      availableDates.value = [...(data.available_dates || [])].sort();
      // 未带日期时后端按最新一天返回，该日报告缺失时也停在这一天的空态
      currentDate.value = params.date || latestDate.value;
      reportToTime.value = '';
      content.value = '';
      if (data.report_status === 'not_connected') {
        status.value = 'unsupported';
        return;
      }
      if (availableDates.value.length < 1) {
        status.value = 'empty';
        return;
      }
      if (!data.has_report) {
        status.value = 'noReport';
        return;
      }
      reportToTime.value = data.report_to_time;
      const reportShare = await getReportShare({ record_id: data.report_id });
      if (currentRequestId !== requestId) {
        return;
      }
      content.value = reportShare.content;
      status.value = 'report';
    } catch {
      if (currentRequestId === requestId) {
        status.value = '';
      }
    } finally {
      if (currentRequestId === requestId) {
        loading.value = false;
      }
    }
  };

  return {
    availableDates,
    content,
    currentDate,
    fetchReport,
    latestDate,
    loading,
    reportToTime,
    status,
  };
};
