<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div
    ref="root"
    class="cluster-detail-health-report">
    <Toolbar
      :available-dates="availableDates"
      :date="currentDate"
      :latest-date="latestDate"
      :report-to-time="reportToTime"
      @change="handleDateChange" />
    <BkLoading :loading="loading">
      <div
        ref="report"
        class="cluster-detail-health-report-content">
        <ReportContent
          :content="content"
          :date="currentDate"
          :status="status"
          @anchor="handleAnchor"
          @panel-change="handlePanelChange" />
      </div>
    </BkLoading>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useRoute, useRouter } from 'vue-router';

  import { URL_HEALTH_REPORT_DATE_KEY } from '../../constants';

  import ReportContent from './components/ReportContent.vue';
  import Toolbar from './components/Toolbar.vue';
  import { parseReportDate, useHealthReport } from './hooks/useHealthReport';

  interface Props {
    clusterData: {
      bk_biz_id: number;
      master_domain: string;
    };
  }

  type Emits = (e: 'panel-change', value: string) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const route = useRoute();
  const router = useRouter();

  const rootRef = useTemplateRef('root');
  const reportRef = useTemplateRef('report');

  const { availableDates, content, currentDate, fetchReport, latestDate, loading, reportToTime, status } =
    useHealthReport();

  const urlDate = computed(() => parseReportDate(route.query[URL_HEALTH_REPORT_DATE_KEY]));

  // 数据日期由 URL 驱动，换期、刷新、从分享页带入都走这里
  watch(
    urlDate,
    () => {
      fetchReport({
        bk_biz_id: props.clusterData.bk_biz_id,
        cluster_domain: props.clusterData.master_domain,
        date: urlDate.value || undefined,
      });
    },
    {
      immediate: true,
    },
  );

  // 空字符串表示回到最新：去掉 URL 日期，不带日期请求
  const handleDateChange = (value: string) => {
    router.replace({
      query: value
        ? {
            ...route.query,
            [URL_HEALTH_REPORT_DATE_KEY]: value,
          }
        : _.omit(route.query, URL_HEALTH_REPORT_DATE_KEY),
    });
  };

  // 报告内锚点：iframe 不滚动，由本组件的滚动容器定位
  const handleAnchor = (top: number) => {
    if (!rootRef.value || !reportRef.value) {
      return;
    }
    const offset = reportRef.value.getBoundingClientRect().top - rootRef.value.getBoundingClientRect().top;
    rootRef.value.scrollTo({
      behavior: 'smooth',
      top: rootRef.value.scrollTop + offset + top,
    });
  };

  const handlePanelChange = (panel: string) => {
    emits('panel-change', panel);
  };
</script>
<style lang="less">
  .cluster-detail-health-report {
    height: 100%;
    padding: 16px 0;
    overflow-y: auto;

    .cluster-detail-health-report-content {
      min-height: 260px;
    }
  }
</style>
