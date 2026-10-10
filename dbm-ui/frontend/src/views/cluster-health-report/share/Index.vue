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
    class="cluster-health-report-share">
    <Teleport to="#dbContentTitleAppend">
      <BkButton
        v-if="detailRouteName"
        class="ml-16"
        text
        theme="primary"
        @click="handleOpenDetail()">
        {{ t('打开集群详情') }}
      </BkButton>
    </Teleport>
    <BkLoading :loading="isClusterLoading || loading">
      <div class="cluster-health-report-share-main">
        <div class="cluster-health-report-share-head">
          <div class="cluster-health-report-share-domain">{{ domain || '--' }}</div>
          <div class="cluster-health-report-share-meta">
            <span>
              {{ t('集群名称') }}：
              <span class="cluster-health-report-share-value">{{ clusterInfo?.cluster_name || '--' }}</span>
            </span>
            <span>
              ID：
              <span class="cluster-health-report-share-value">{{ clusterInfo?.id || '--' }}</span>
            </span>
            <span>
              {{ t('业务') }}：
              <span class="cluster-health-report-share-value">{{ bizName || '--' }}</span>
            </span>
            <span>
              {{ t('DBA 负责人') }}：
              <span class="cluster-health-report-share-value">
                <bk-user-display-name
                  v-if="dbaUsers.length"
                  :user-id="dbaUsers.join(',')" />
                <template v-else>--</template>
              </span>
            </span>
            <span>
              {{ t('架构') }}：
              <span class="cluster-health-report-share-value">{{ architecture || '--' }}</span>
            </span>
            <span>
              {{ t('地域') }}：
              <span class="cluster-health-report-share-value">{{ regionDisplay || '--' }}</span>
            </span>
          </div>
        </div>
        <div ref="report">
          <ReportContent
            :content="content"
            :date="currentDate"
            :status="displayStatus"
            @anchor="handleAnchor"
            @panel-change="handleOpenDetail" />
        </div>
      </div>
    </BkLoading>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import { getAdmins } from '@services/source/dbadmin';
  import { filterClusters } from '@services/source/dbbase';

  import { useGlobalBizs } from '@stores';

  import { clusterTypeInfos } from '@common/const';

  import ReportContent from '@views/db-manage/common/cluster-details/components/health-report/components/ReportContent.vue';
  import {
    parseReportDate,
    useHealthReport,
  } from '@views/db-manage/common/cluster-details/components/health-report/hooks/useHealthReport';
  import {
    URL_CLUSTER_DETAIL_MEMO_KEY,
    URL_HEALTH_REPORT_DATE_KEY,
  } from '@views/db-manage/common/cluster-details/constants';
  import { clusterTypeListPageMap } from '@views/db-manage/const/clusterTypeListPageMap';

  // filterClusters 的泛型声明里没有 region，按返回字段补上
  type ClusterInfo = { region: string } & ServiceReturnType<typeof filterClusters>[number];

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const globalBizsStore = useGlobalBizs();

  const bizId = window.PROJECT_CONFIG.BIZ_ID;
  const domain = String(route.query.domain || '');
  const urlDate = parseReportDate(route.query.date);

  const rootRef = useTemplateRef('root');
  const reportRef = useTemplateRef('report');

  const isClusterLoading = ref(false);
  const clusterInfo = ref<ClusterInfo>();
  const dbaUsers = ref<string[]>([]);

  const { content, currentDate, fetchReport, loading, status } = useHealthReport();

  const bizName = computed(() => globalBizsStore.bizIdMap.get(bizId)?.name);
  const architecture = computed(() =>
    clusterInfo.value ? clusterTypeInfos[clusterInfo.value.cluster_type]?.name : '',
  );
  const regionDisplay = computed(() => {
    if (!clusterInfo.value) {
      return '';
    }
    const { region } = clusterInfo.value;
    return !region || region === 'default' ? t('随机') : region;
  });
  const detailRouteName = computed(() =>
    clusterInfo.value ? clusterTypeListPageMap[clusterInfo.value.cluster_type] : '',
  );
  // 缺少域名或查不到集群时不请求报告，按「暂不支持」展示
  const displayStatus = computed(() => {
    if (isClusterLoading.value) {
      return '';
    }
    return clusterInfo.value ? status.value : 'unsupported';
  });

  const fetchData = async () => {
    if (!domain) {
      return;
    }
    isClusterLoading.value = true;
    try {
      const [clusterList, adminResult] = await Promise.all([
        filterClusters<ClusterInfo>({
          bk_biz_id: bizId,
          exact_domain: domain,
        }),
        getAdmins({
          bk_biz_id: bizId,
        }),
      ]);
      const [cluster] = clusterList;
      clusterInfo.value = cluster;
      if (!cluster) {
        return;
      }
      dbaUsers.value = adminResult.data.find((item) => item.db_type === cluster.db_type)?.users || [];
      fetchReport({
        bk_biz_id: bizId,
        cluster_domain: cluster.master_domain,
        date: urlDate || undefined,
      });
    } finally {
      isClusterLoading.value = false;
    }
  };

  // 不传 panel 时：已接入落到健康报告 Tab 并带上当前这一份的日期，未接入落到默认 Tab
  const handleOpenDetail = (panel?: string) => {
    if (!clusterInfo.value || !detailRouteName.value) {
      return;
    }
    let query: Record<string, string> = {};
    if (panel) {
      query = {
        [URL_CLUSTER_DETAIL_MEMO_KEY]: panel,
      };
    } else if (status.value && status.value !== 'unsupported') {
      query = {
        [URL_CLUSTER_DETAIL_MEMO_KEY]: 'healthReport',
        ...(currentDate.value ? { [URL_HEALTH_REPORT_DATE_KEY]: currentDate.value } : {}),
      };
    }
    const { href } = router.resolve({
      name: detailRouteName.value,
      params: {
        clusterId: clusterInfo.value.id,
      },
      query,
    });
    window.open(href);
  };

  // 报告内锚点：iframe 不滚动，由页面滚动容器定位
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

  fetchData();
</script>
<style lang="less">
  .cluster-health-report-share {
    height: 100%;
    overflow-y: auto;

    .cluster-health-report-share-main {
      max-width: 1100px;
      min-height: 260px;
      padding: 24px;
      margin: 0 auto;
    }

    .cluster-health-report-share-head {
      padding-bottom: 16px;
      margin-bottom: 16px;
      border-bottom: 1px solid #dcdee5;
    }

    .cluster-health-report-share-domain {
      margin-bottom: 8px;
      font-size: 16px;
      color: #313238;
    }

    .cluster-health-report-share-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px 24px;
      font-size: 12px;
      color: #979ba5;
    }

    .cluster-health-report-share-value {
      color: #63656e;
    }
  }
</style>
