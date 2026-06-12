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
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import { getListClusterModuleConfFiles } from '@services/source/configs';

  import { ClusterTypes } from '@common/const';

  import { getConfigureState, saveConfigureState } from '@/views/db-configure/utils/configureState';

  interface Props {
    clusterId?: number;
    dbModuleId?: number;
    showOperationRecordTab?: boolean;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const route = useRoute();
  const router = useRouter();

  const clusterType = computed(() => (route.params.clusterType as ClusterTypes) || ClusterTypes.TENDBSINGLE);

  /** 初始化 activeTab（优先从 sessionStorage 恢复） */
  const getInitialActiveTab = (): string => {
    const savedState = getConfigureState();
    if (savedState.activeTab) {
      return savedState.activeTab;
    }
    const urlConfFile = (route.params.tabName as string) || '';
    // 如果从 URL 获取了 confFile，保存到 sessionStorage
    if (urlConfFile) {
      saveConfigureState({ activeTab: urlConfFile });
    }
    return urlConfFile;
  };

  const activeTab = ref(getInitialActiveTab());
  const confTabs = ref<ServiceReturnType<typeof getListClusterModuleConfFiles>>([]);

  /** 同步 confFile 到 URL 并保存 tab 到 sessionStorage */
  watch(activeTab, (value) => {
    router.replace({
      params: {
        ...route.params,
        tabName: value || undefined,
      },
    });

    // 保存 activeTab 到 sessionStorage（存储 conf_file 字符串）
    if (value) {
      saveConfigureState({ activeTab: value });
    }
  });

  const { run: fetchConfTabs } = useRequest(getListClusterModuleConfFiles, {
    manual: true,
    onSuccess(res) {
      const base = res;
      if (props.showOperationRecordTab) {
        base.push({
          conf_file: 'operationRecord',
          conf_type: 'operationRecord',
          name: t('配置变更记录'),
        });
      }

      confTabs.value = base;

      // 从 sessionStorage 恢复 activeTab
      const savedState = getConfigureState();
      if (!activeTab.value && savedState.activeTab) {
        if (base.find((tab) => tab.conf_file === savedState.activeTab)) {
          activeTab.value = savedState.activeTab;
          return;
        }
      }

      // 如果没有保存的状态，使用默认值
      if (!activeTab.value && res.length > 0) {
        activeTab.value = res[0].conf_file || '';
      }
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
