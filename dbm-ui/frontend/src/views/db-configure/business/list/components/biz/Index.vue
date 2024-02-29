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
  <div class="biz-content">
    <BkTab
      v-model:active="state.activatedTab"
      type="unborder-card">
      <BkTabPanel
        v-for="tab of state.tabs"
        :key="tab.confType"
        :label="tab.name"
        :name="tab.confType"
        render-directive="if">
        <ConfigDatabase :conf-type="tab.confType" />
      </BkTabPanel>
    </BkTab>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { ClusterTypesValues } from '@common/const';

  import { extraClusterConfs, getDefaultConf } from '@views/db-configure/common/const';
  import type { ConfType } from '@views/db-configure/common/types';

  import ConfigDatabase from './ConfigDatabase.vue';

  const { t } = useI18n();
  const route = useRoute();
  const state = reactive({
    activatedTab: 'dbconf',
    tabs: [] as ConfType[],
  });

  /**
   * tabs 设置
   */
  watch(
    () => route.params.clusterType,
    (type) => {
      const clusterType = type as ClusterTypesValues;
      const tabs = [getDefaultConf(clusterType, t('配置列表'))];
      // 添加额外配置
      const extraTabs = extraClusterConfs[clusterType];
      if (extraTabs) {
        tabs.push(...extraTabs);
      }
      state.tabs = tabs;
    },
    { immediate: true },
  );
</script>
