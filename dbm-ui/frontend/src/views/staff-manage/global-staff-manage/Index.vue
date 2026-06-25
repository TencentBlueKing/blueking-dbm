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
  <div class="dba-manage-global">
    <div class="list-page">
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
      <div v-if="activeTopTab === 'person-manage'">
        <DbaManage />
      </div>
      <div v-if="activeTopTab === 'biz-manage'">
        <BizManage />
      </div>
      <div v-if="activeTopTab === 'oplog'">
        <OperationRecord />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import BizManage from './components/biz-manage/Index.vue';
  import DbaManage from './components/dba-manage/Index.vue';
  import OperationRecord from './components/operation-record/Index.vue';

  type TopTab = 'person-manage' | 'biz-manage' | 'oplog';

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();

  const topTabs: {
    key: TopTab;
    label: string;
  }[] = [
    { key: 'person-manage', label: t('DBA 配置') },
    { key: 'biz-manage', label: t('业务管理') },
    { key: 'oplog', label: t('操作记录') },
  ];
  const activeTopTab = ref<TopTab>((route.params.tabType as TopTab) || 'person-manage');

  watch(activeTopTab, () => {
    router.replace({
      params: {
        tabType: activeTopTab.value,
      },
    });
  });
</script>

<style lang="less" scoped>
  .dba-manage-global {
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
  }
</style>
