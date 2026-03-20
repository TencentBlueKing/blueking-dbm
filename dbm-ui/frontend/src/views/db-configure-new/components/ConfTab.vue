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
  <BkTab
    v-model:active="activeTab"
    type="card-tab">
    <BkTabPanel
      v-for="tab of confTabs"
      :key="tab.conf_file"
      :label="tab.name"
      :name="tab.conf_file"
      render-directive="if">
      <slot :tab="tab" />
    </BkTabPanel>
  </BkTab>
</template>

<script setup lang="ts">
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import { getListClusterModuleConfFiles } from '@services/source/configs';

  import { ClusterTypes } from '@common/const';

  interface Props {
    clusterId?: number;
    dbModuleId?: number;
  }

  const props = defineProps<Props>();

  const route = useRoute();

  const clusterType = computed(() => (route.params.clusterType as ClusterTypes) || ClusterTypes.TENDBSINGLE);

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
    [() => props.clusterId, () => props.dbModuleId],
    () => {
      fetchConfTabs({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        cluster_id: props.clusterId || undefined,
        db_module_id: props.dbModuleId || undefined,
        meta_cluster_type: clusterType.value,
      });
    },
    { immediate: true },
  );
</script>
