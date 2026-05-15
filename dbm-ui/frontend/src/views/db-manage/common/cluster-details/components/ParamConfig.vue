<!--
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
-->

<template>
  <div class="conf-tab-wrapper mt-16">
    <BkTab
      v-model:active="activeTab"
      type="unborder-card">
      <BkTabPanel
        v-for="tab of confTabs"
        :key="tab.conf_file"
        :label="tab.name"
        :name="tab.conf_file"
        render-directive="if">
        <BkAlert
          class="mb-16"
          closable
          theme="info"
          :title="t('集群配置参数说明')" />
        <ParamTable
          :cluster="cluster"
          :conf-type="tab.conf_type"
          level-name="cluster"
          :level-value="cluster.master_domain"
          selectable
          :version="tab.conf_file" />
      </BkTabPanel>
    </BkTab>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getListClusterModuleConfFiles } from '@services/source/configs';

  import type { ClusterTypes } from '@common/const';

  import ParamTable from './ParamTable.vue';

  interface Props {
    cluster: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const activeTab = ref('');
  const confTabs = ref<ServiceReturnType<typeof getListClusterModuleConfFiles>>([]);

  const { run: fetchConfTabs } = useRequest(getListClusterModuleConfFiles, {
    manual: true,
    onSuccess(res) {
      confTabs.value = res;
      activeTab.value = res[0]?.conf_file || '';
    },
  });

  watch(
    () => props.cluster.id,
    () => {
      fetchConfTabs({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        cluster_id: props.cluster.id,
        meta_cluster_type: props.cluster.cluster_type as string,
      });
    },
    { immediate: true },
  );
</script>

<style lang="less">
  .conf-tab-wrapper .bk-tab.bk-tab--unborder-card {
    .bk-tab-header {
      background: transparent;
    }

    .bk-tab-header-item {
      border: none !important;
      background: transparent !important;

      &::before,
      &::after {
        display: none !important;
      }

      &.is-active {
        color: #3a84ff;
      }
    }

    .bk-tab-content {
      height: auto;
      padding: 16px 0;
    }

    .bk-tab-panel {
      padding: 0;
    }
  }
</style>
