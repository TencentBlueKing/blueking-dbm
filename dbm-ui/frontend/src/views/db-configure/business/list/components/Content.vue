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
  <BkResizeLayout
    :border="false"
    class="database-content"
    collapsible
    initial-divide="312px"
    :max="500"
    :min="312">
    <template #aside>
      <ConfigTree ref="configTreeRef" />
    </template>
    <template #main>
      <div
        v-if="configTreeRef?.treeState?.activeNode"
        :key="configTreeRef.treeState.activeNode.id"
        class="content-details">
        <Component
          :is="activeComponent"
          :cluster-type="clusterType" />
      </div>
    </template>
  </BkResizeLayout>
</template>
<script setup lang="ts">
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import { getListClusterModuleConfFiles } from '@services/source/configs.ts';

  import { ClusterTypes, ConfLevels } from '@common/const';

  import ConfigTree from '@views/db-configure/components/TopoTree.vue';

  import ConfigBusiness from './biz/Index.vue';
  import ConfigModule from './module/Index.vue';

  const route = useRoute();

  const configTreeRef = ref<InstanceType<typeof ConfigTree>>();
  // 提供配置文件列表给子组件
  const confTabs = ref<ServiceReturnType<typeof getListClusterModuleConfFiles>>([]);
  provide('confTabs', confTabs);

  // 将当前选中的树节点 provide 给子组件（biz/module）
  const activeTreeNode = computed(() => configTreeRef.value?.treeState?.activeNode);
  provide('treeNode', readonly(activeTreeNode));

  // 提供刷新树的方法给子组件
  const refreshTree = () => {
    configTreeRef.value?.handleRefresh?.();
  };
  provide('refreshTree', refreshTree);

  const clusterType = computed(() => (route.params.clusterType as ClusterTypes) || ClusterTypes.TENDBSINGLE);

  const activeComponent = computed(() => {
    const activeNode = configTreeRef.value?.treeState?.activeNode;
    if (!activeNode) return '';

    if (activeNode.levelType === ConfLevels.APP) {
      return ConfigBusiness;
    }
    if (activeNode.levelType === ConfLevels.MODULE) {
      return ConfigModule;
    }
    return '';
  });

  const { run: fetchConfTabs } = useRequest(getListClusterModuleConfFiles, {
    manual: true,
    onSuccess(res) {
      confTabs.value = res;
    },
  });

  watch(
    () => activeTreeNode.value?.id,
    (moduleId) => {
      if (moduleId) {
        fetchConfTabs({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          db_module_id: moduleId,
          meta_cluster_type: clusterType.value,
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  .database-content {
    height: 100%;

    :deep(.bk-resize-layout-aside) {
      &::after {
        display: none;
      }
    }
  }

  .content-details {
    margin: 20px 24px;
  }
</style>
