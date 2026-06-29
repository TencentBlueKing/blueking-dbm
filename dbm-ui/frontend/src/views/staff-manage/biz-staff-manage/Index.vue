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
  <div class="dba-manage-biz">
    <BkLoading
      :loading="isLoading"
      style="height: 100%">
      <template v-if="currentBizInfo?.status === 'managed'">
        <BkTab
          v-model:active="activeTopTab"
          class="db-tab"
          type="unborder-card">
          <BkTabPanel
            v-for="tab of topTabs"
            :key="tab.key"
            :label="tab.label"
            :name="tab.key" />
        </BkTab>
        <div v-if="activeTopTab === 'person'">
          <DbaManage
            :active-top-tab="activeTopTab"
            :count-data="clusterInstanceCountData" />
        </div>
        <div v-if="activeTopTab === 'oplog'">
          <OperationRecord />
        </div>
      </template>
      <BkException
        v-else
        class="empty-exception"
        :description="
          t('如需管理该业务的数据库，请联系 DBA Leader 完成纳管。纳管后即可在此页面维护各组件类型的 DBA 配置。')
        "
        scene="page"
        :title="t('当前业务尚未纳入 DBA 管理')"
        type="empty" />
    </BkLoading>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { queryClusterInstanceCount } from '@services/source/dbbase';

  import { useGlobalBizs } from '@stores';

  import DbaManage from './components/dba-manage/Index.vue';
  import OperationRecord from './components/operation-record/Index.vue';

  type TopTab = 'person' | 'oplog';

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();
  const { currentBizInfo } = useGlobalBizs();

  const topTabs = [
    { key: 'person', label: t('DBA 配置') },
    { key: 'oplog', label: t('操作记录') },
  ];

  const activeTopTab = ref<TopTab>((route.params.tabType as TopTab) || 'person');

  watch(activeTopTab, () => {
    router.replace({
      params: {
        tabType: activeTopTab.value,
      },
    });
  });

  const { data: clusterInstanceCountData, loading: isLoading } = useRequest(queryClusterInstanceCount, {
    defaultParams: [{ bk_biz_id: window.PROJECT_CONFIG.BIZ_ID }],
  });
</script>

<style lang="less">
  .dba-manage-biz {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: #f5f7fa;

    .db-tab {
      padding: 0 24px;
      background: #fff;
      // box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);

      .bk-tab-content {
        display: none;
      }
    }

    .empty-exception {
      display: flex;
      height: 100%;
      background-color: #fff;
      align-items: center;
      justify-content: center;
    }
  }
</style>
