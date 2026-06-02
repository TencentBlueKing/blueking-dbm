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
  <div class="module-content">
    <BkLoading
      :loading="loading"
      style="height: 100%"
      :z-index="12">
      <!-- 模块头部信息 -->
      <DbCard
        class="module-header-card"
        mode="collapse"
        :title="treeNode?.name">
        <template #desc>
          <div class="module-header-actions">
            <BkTag theme="info">
              {{ t('模块配置') }}
            </BkTag>
            <BkButton
              size="small"
              theme="primary"
              @click="handleCloneModule">
              {{ t('克隆') }}
            </BkButton>
            <BkPopConfirm
              :cancel-text="t('取消')"
              :confirm-config="{ theme: 'danger' } as any"
              :confirm-text="t('确认删除')"
              :disabled="moduleInfo.relatedClusterCount > 0"
              :title="t('确认删除？')"
              trigger="click"
              :width="275"
              @confirm="handleDeleteModule">
              <template #content>
                <div
                  class="mb-16"
                  style="line-height: 20px">
                  <p class="mb-6">
                    {{ t('模块名称_:_name', { name: moduleInfo.moduleName }) }}
                  </p>
                  <p>
                    {{ t('删除后无法恢复，请谨慎修改！') }}
                  </p>
                </div>
              </template>
              <span @click.stop>
                <BkButton
                  v-bk-tooltips="{
                    content: t('关联集群不为空，不能删除'),
                    disabled: moduleInfo.relatedClusterCount <= 0,
                  }"
                  :disabled="moduleInfo.relatedClusterCount > 0"
                  size="small">
                  {{ t('删除') }}
                </BkButton>
              </span>
            </BkPopConfirm>
          </div>
        </template>
        <div class="module-info-bar">
          <span class="module-info-item">
            <span class="module-info-label">{{ t('ID') }}：</span>{{ moduleInfo.moduleId || '--' }}
          </span>
          <span class="module-info-item">
            <span class="module-info-label">{{ t('存储层版本') }}：</span>{{ moduleInfo.version || '--' }}
          </span>
          <span
            v-if="isTenDBCluster"
            class="module-info-item">
            <span class="module-info-label">{{ t('接入层版本') }}：</span>{{ moduleInfo.spiderVersion || '--' }}
          </span>
          <span class="module-info-item">
            <span class="module-info-label">{{ t('字符集') }}：</span>{{ moduleInfo.charset || '--' }}
          </span>
          <span class="module-info-item related-clusters-wrapper">
            <span class="module-info-label">{{ t('关联集群') }}：</span>
            <span
              v-if="moduleInfo.relatedClusterCount > 0"
              ref="relatedClustersRef"
              class="related-clusters-count">
              {{ moduleInfo.relatedClusterCount }}
            </span>
            <span v-else>--</span>
          </span>
          <span class="module-info-item">
            <span class="module-info-label">{{ t('最近更新') }}：</span>{{ moduleInfo.updatedBy || '--' }} /
            {{ moduleInfo.updatedAt || '--' }}
          </span>
        </div>
      </DbCard>

      <!-- 参数配置 / 操作记录 tabs -->
      <BkTab
        v-model:active="activeTopTab"
        class="module-top-tab"
        type="unborder-card">
        <BkTabPanel
          :label="t('参数配置')"
          name="paramConfig"
          render-directive="if">
          <BkAlert
            class="mt-16 mb-16"
            closable
            theme="info"
            :title="t('模块配置参数说明')" />
          <!-- 参数配置子 tabs -->
          <ConfTab
            class="module-conf-tab mt-16"
            :db-module-id="moduleInfo.moduleId">
            <template #default="{ tab }">
              <ParamTable
                :cluster-type="clusterType"
                :conf-type="tab.conf_type"
                level-name="module"
                :level-value="moduleInfo.moduleId"
                selectable
                :version="tab.conf_file" />
            </template>
          </ConfTab>
        </BkTabPanel>
        <BkTabPanel
          :label="t('操作记录')"
          name="operationRecord"
          render-directive="if">
          <div class="module-operation-record">
            <OperationRecord
              level-name="module"
              :level-value="moduleInfo.moduleId" />
          </div>
        </BkTabPanel>
      </BkTab>
    </BkLoading>
  </div>
</template>

<script setup lang="ts">
  import type { Instance } from 'tippy.js';
  import type { ComputedRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import { deleteModuleConfig, getLevelConfig } from '@services/source/configs';

  import { clusterTypeInfos, ClusterTypes, DBTypes } from '@common/const';
  import { dbTippy } from '@common/tippy';

  import type { TreeData, TreeState } from '@views/db-configure-new/common/types';
  import ConfTab from '@views/db-configure-new/components/ConfTab.vue';
  import ParamTable from '@views/db-configure-new/components/ParamTable.vue';
  import { useTreeData } from '@views/db-configure-new/hooks/useTreeData';

  import { messageSuccess } from '@utils';

  import OperationRecord from '../OperationRecord.vue';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  const treeState = reactive<TreeState>({
    data: [],
    isAnomalies: false,
    loading: false,
    search: '',
  });
  const { createModule } = useTreeData(treeState);

  const treeNode = inject<ComputedRef<TreeData>>('treeNode');

  const clusterType = computed(() => (route.params.clusterType as ClusterTypes) || ClusterTypes.TENDBSINGLE);
  const dbType = computed(() => clusterTypeInfos[clusterType.value].dbType);

  const moduleInfo = reactive({
    charset: '',
    moduleId: 0,
    moduleName: '',
    relatedClusterCount: 0,
    relatedClusters: '',
    spiderVersion: '',
    updatedAt: '',
    updatedBy: '',
    version: '',
  });

  /** 是否为 TenDBCluster（含接入层 spider，需要展示接入层版本） */
  const isTenDBCluster = computed(() => clusterType.value === ClusterTypes.TENDBCLUSTER);

  /** 顶部 tabs: 参数配置 / 操作记录 */
  const activeTopTab = ref((route.query.topTab as string) || 'paramConfig');

  /** 同步顶部 tab 到 URL */
  watch(activeTopTab, (value) => {
    router.replace({
      query: {
        ...route.query,
        topTab: value || undefined,
      },
    });
  });

  /** 获取模块部署信息 */
  const { loading, run: fetchModuleConfig } = useRequest(getLevelConfig, {
    manual: true,
    onSuccess(result) {
      result.conf_items.forEach((item) => {
        if (item.conf_name === 'db_version') {
          moduleInfo.version = item.conf_value ?? '';
        } else if (item.conf_name === 'charset') {
          moduleInfo.charset = item.conf_value ?? '';
        } else if (item.conf_name === 'spider_version') {
          moduleInfo.spiderVersion = item.conf_value ?? '';
        }
      });
      moduleInfo.updatedBy = result.updated_by || '';
      moduleInfo.updatedAt = result.updated_at || '';
    },
  });

  /** 构建关联集群信息 */
  const buildRelatedClusters = () => {
    if (!treeNode?.value) return;

    // 模块节点的关联集群存放在独立字段 clusters，避免污染 BkTree 的渲染数据
    const clusterNodes = treeNode.value.clusters || [];

    if (clusterNodes.length > 0) {
      moduleInfo.relatedClusterCount = clusterNodes.length;
      moduleInfo.relatedClusters = clusterNodes.map((node) => node.name).join(', ');
    } else {
      moduleInfo.relatedClusterCount = 0;
      moduleInfo.relatedClusters = '';
    }
  };

  /** 关联集群 tooltip 纵向展示 */
  const relatedClustersRef = ref<HTMLElement>();
  let relatedClustersTippy: Instance | null = null;

  const relatedClustersTooltip = computed(() => {
    if (!moduleInfo.relatedClusters) return '';
    const items = moduleInfo.relatedClusters.split(', ');
    return `
      <div class="related-clusters-tooltip">
        <div class="related-clusters-list">
          ${items.map((name) => `<div class="related-cluster-item">${name}</div>`).join('')}
        </div>
      </div>
    `;
  });

  watch(
    [relatedClustersRef, relatedClustersTooltip],
    ([el, content]) => {
      relatedClustersTippy?.destroy();
      if (el && content) {
        relatedClustersTippy = dbTippy(el, {
          allowHTML: true,
          appendTo: () => document.body,
          arrow: true,
          content,
          hideOnClick: true,
          interactive: true,
          placement: 'top',
          trigger: 'mouseenter click',
          zIndex: 9999,
        });
      }
    },
    { immediate: true },
  );

  /** 监听树节点变化 */
  watch(
    () => treeNode,
    (node, old) => {
      if (node && node.value && node.value.treeId !== old?.value?.treeId) {
        moduleInfo.version = '';
        moduleInfo.charset = '';
        moduleInfo.spiderVersion = '';
        moduleInfo.moduleId = node.value.id;
        moduleInfo.moduleName = node.value.name;

        buildRelatedClusters();

        if ([DBTypes.MYSQL, DBTypes.SQLSERVER, DBTypes.TENDBCLUSTER].includes(dbType.value)) {
          fetchModuleConfig({
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            conf_type: 'deploy',
            level_name: 'module',
            level_value: node.value.id,
            meta_cluster_type: clusterType.value,
            version: 'deploy_info',
          });
        }
      }
    },
    { deep: true, immediate: true },
  );

  /** 克隆模块 */
  const handleCloneModule = () => {
    createModule({
      charset: moduleInfo.charset || '',
      clusterType: clusterType.value,
      confFile: moduleInfo.version || '',
      from: String(route.name),
      moduleId: String(moduleInfo.moduleId),
      moduleName: moduleInfo.moduleName,
    });
  };

  const refreshTree = inject<() => void>('refreshTree');

  /** 删除模块 */
  const { run: runDeleteModule } = useRequest(deleteModuleConfig, {
    manual: true,
    onSuccess() {
      messageSuccess(t('删除成功'));
      refreshTree?.();
    },
  });

  const handleDeleteModule = () => {
    runDeleteModule({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      db_module_id: moduleInfo.moduleId,
      meta_cluster_type: clusterType.value,
    });
  };

  onUnmounted(() => {
    relatedClustersTippy?.destroy();
  });
</script>

<style lang="less" scoped>
  .module-content {
    height: 100%;
  }

  .module-header-card {
    box-shadow: none;
    padding-bottom: 0;

    :deep(.db-card-content) {
      padding: 0;
    }
  }

  .module-header-actions {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .module-info-bar {
    display: flex;
    align-items: center;
    gap: 32px;
    padding: 12px 24px;
  }

  .module-info-item {
    display: inline-flex;
    align-items: center;
    font-size: 12px;
    line-height: 20px;
    white-space: nowrap;
  }

  .related-clusters-wrapper {
    .related-clusters-count {
      margin-left: 4px;
      font-weight: 700;
      color: #3a84ff;
      cursor: default;
    }
  }

  .module-top-tab {
    :deep(.bk-tab-header) {
      box-shadow: none;
      border-bottom: none;
    }

    :deep(.bk-tab-content) {
      padding: 0;
      background: #f6f7fb;
    }

    :deep(.bk-tab-header-active-bar) {
      width: 56px !important;
      bottom: 2px !important;
      margin: 0 20px !important;
    }
  }

  .module-conf-tab {
    :deep(.bk-tab-content) {
      padding: 16px 16px 0;
      background: #fff;
    }
  }

  .module-operation-record {
    background: #fff;
    margin-top: 16px;
    padding-top: 16px;
  }
</style>

<style lang="less">
  .related-clusters-tooltip {
    padding: 8px 0;

    .related-clusters-list {
      max-height: 240px;
      overflow-y: auto;
      padding: 0 12px;
    }

    .related-cluster-item {
      line-height: 28px;
    }
  }
</style>
