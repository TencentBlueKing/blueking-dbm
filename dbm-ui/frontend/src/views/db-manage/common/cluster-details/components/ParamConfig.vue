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
        <OperationRecord
          v-if="tab.conf_type === 'operationRecord'"
          :cluster-type="cluster.cluster_type"
          level-name="cluster"
          :level-value="cluster.master_domain" />
        <template v-else>
          <BkAlert
            class="mb-16"
            closable
            theme="info">
            <template v-if="hasModule">
              {{ t('参数值默认继承自') }}
              <a
                class="alert-link"
                @click="openModuleConfig(tab)">
                {{ cluster.db_module_name }} {{ t('模块配置') }}
              </a>
              {{
                t(
                  ' ；模块配置更新时，未自定义的参数值会自动同步。修改后将转为「自定义」，不再随模块配置更新；新增实例将使用该集群当前配置。可通过「恢复默认」重新继承模块配置。',
                )
              }}
            </template>
            <template v-else>
              {{ t('参数值默认继承自') }}
              <a
                class="alert-link"
                @click="openBusinessConfig(tab)">
                {{ t('业务配置') }}
              </a>
              {{
                t(
                  ' ；业务配置更新时，未自定义的参数值会自动同步。修改后将转为「自定义」，不再随业务配置更新；新增实例将使用该集群当前配置。可通过「恢复默认」重新继承业务配置。',
                )
              }}
            </template>
          </BkAlert>
          <ParamTable
            :cluster-id="cluster.id"
            :cluster-type="cluster.cluster_type"
            :conf-type="tab.conf_type"
            :config-name="tab.name"
            level-name="cluster"
            :level-value="cluster.master_domain"
            :namespace="tab.namespace"
            selectable
            :version="tab.conf_file" />
        </template>
      </BkTabPanel>
    </BkTab>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import { getListClusterModuleConfFiles } from '@services/source/configs';

  import { ClusterTypes } from '@common/const';

  import OperationRecord from '@views/db-configure/business/list/components/OperationRecord.vue';
  import ParamTable from '@views/db-configure/components/ParamTable.vue';

  import { URL_PARAM_CONF_TAB_KEY } from '../constants';

  interface Props {
    cluster: {
      cluster_type: ClusterTypes;
      db_module_id: number;
      db_module_name: string;
      id: number;
      major_version: string;
      master_domain: string;
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  /** 支持模块的集群类型列表 */
  const MODULE_CLUSTER_TYPES = [
    ClusterTypes.SQLSERVER_HA,
    ClusterTypes.SQLSERVER_SINGLE,
    ClusterTypes.TENDBCLUSTER,
    ClusterTypes.TENDBHA,
    ClusterTypes.TENDBSINGLE,
  ];

  /** 当前集群是否支持模块配置 */
  const hasModule = computed(() => MODULE_CLUSTER_TYPES.includes(props.cluster.cluster_type));

  /** 新开 tab 打开模块配置页（DbConfigureList） */
  const openModuleConfig = (tab: ServiceReturnType<typeof getListClusterModuleConfFiles>[0]) => {
    const href = router.resolve({
      name: 'DbConfigureList',
      params: {
        clusterType: props.cluster.cluster_type,
        parentId: `app-${window.PROJECT_CONFIG.BIZ_ID}`,
        tabName: tab.conf_file,
        treeId: `module-${props.cluster.db_module_id}`,
      },
    }).href;
    window.open(href, '_blank');
  };

  /** 新开 tab 打开业务配置详情页（DbConfigureDetail） */
  const openBusinessConfig = (tab: ServiceReturnType<typeof getListClusterModuleConfFiles>[0]) => {
    const href = router.resolve({
      name: 'DbConfigureDetail',
      params: {
        clusterType: props.cluster.cluster_type,
        confType: tab.conf_type,
        version: tab.conf_file,
      },
    }).href;
    window.open(href, '_blank');
  };

  const activeTab = ref('');
  const confTabs = ref<ServiceReturnType<typeof getListClusterModuleConfFiles>>([]);

  const { run: fetchConfTabs } = useRequest(getListClusterModuleConfFiles, {
    manual: true,
    onSuccess(res) {
      confTabs.value = [
        ...res,
        {
          conf_file: 'operationRecord',
          conf_type: 'operationRecord',
          name: t('配置变更记录'),
          namespace: 'operationRecord',
        },
      ];
      // 优先从 URL 参数恢复 activeTab
      const urlTab = route.query[URL_PARAM_CONF_TAB_KEY];
      const isValidTab = confTabs.value.some((tab) => tab.conf_file === urlTab);
      if (isValidTab) {
        activeTab.value = String(urlTab);
      } else {
        activeTab.value = res[0]?.conf_file || '';
      }
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

  // activeTab 变化时同步到 URL
  watch(activeTab, (value) => {
    if (value) {
      const query = { ...route.query, [URL_PARAM_CONF_TAB_KEY]: value };
      router.replace({ query });
    }
  });
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

    .alert-link {
      color: #3a84ff;
      cursor: pointer;

      &:hover {
        color: #699df4;
      }
    }
  }
</style>
