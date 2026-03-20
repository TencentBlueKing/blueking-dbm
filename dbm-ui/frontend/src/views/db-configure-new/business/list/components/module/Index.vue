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
        class="module-header-card mb-16"
        mode="collapse"
        :title="treeNode?.name">
        <template #desc>
          <div class="module-header-actions">
            <BkTag theme="info">
              {{ t('模块配置') }}
            </BkTag>
            <AuthTemplate
              action-id="dbconfig_edit"
              class="module-header-actions"
              :resource="dbType">
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
            </AuthTemplate>
          </div>
        </template>
        <Component
          :is="moduleInfoComponent[dbType]"
          ref="moduleInfoRef"
          :module-info="moduleInfo" />
      </DbCard>

      <ConfTab
        class="module-conf-tab"
        :db-module-id="moduleInfo.moduleId"
        show-operation-record-tab>
        <template #default="{ tab }">
          <OperationRecord
            v-if="tab.conf_type === 'operationRecord'"
            level-name="module"
            :level-value="moduleInfo.moduleId" />
          <ParamTable
            v-else
            :cluster-type="clusterType"
            :conf-type="tab.conf_type"
            level-name="module"
            :level-value="moduleInfo.moduleId"
            selectable
            :version="tab.conf_file" />
        </template>
      </ConfTab>
    </BkLoading>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import type { ParameterConfigItem } from '@services/source/configs';
  import { deleteModuleConfig, getLevelConfig } from '@services/source/configs';

  import { clusterTypeInfos, ClusterTypes, DBTypes } from '@common/const';

  import type { ModuleInfo, TreeData, TreeState } from '@views/db-configure-new/common/types';
  import ConfTab from '@views/db-configure-new/components/ConfTab.vue';
  import ParamTable from '@views/db-configure-new/components/ParamTable.vue';
  import { useTreeData } from '@views/db-configure-new/hooks/useTreeData';

  import { messageSuccess } from '@utils';

  import OperationRecord from '../OperationRecord.vue';

  import MySql from './com-factory/MySql.vue';
  import SqlServer from './com-factory/SqlServer.vue';
  import TendbCluster from './com-factory/TendbCluster.vue';

  /** 子组件暴露的方法接口 */
  interface ModuleInfoComponentExposes {
    getResetValues: () => Partial<ModuleInfo>;
    parseConfig: (confItems: ParameterConfigItem[]) => Partial<ModuleInfo>;
  }

  /** 动态组件 ref */
  const moduleInfoRef = ref<ModuleInfoComponentExposes | null>(null);

  const route = useRoute();
  const { t } = useI18n();

  const treeState = reactive<TreeState>({
    data: [],
    isAnomalies: false,
    loading: false,
    search: '',
  });
  const { cloneModule } = useTreeData(treeState);

  const treeNode = inject<ComputedRef<TreeData>>('treeNode');

  const clusterType = computed(() => (route.params.clusterType as ClusterTypes) || ClusterTypes.TENDBSINGLE);
  const dbType = computed(() => clusterTypeInfos[clusterType.value]?.dbType || DBTypes.MYSQL);

  const moduleInfo: ModuleInfo = reactive({
    bufferPercent: '', // 内存分片比率 (SqlServer)
    charset: '',
    maxRemainMemGb: '', // 最大OS保留内存 (SqlServer)
    moduleId: 0,
    moduleName: '',
    relatedClusterCount: 0,
    relatedClusters: '',
    spiderVersion: '', // 接入层版本 (TenDBCluster)
    syncType: '', // 主从方式 (SqlServer)
    systemVersion: '', // 操作系统版本 (SqlServer)
    updatedAt: '',
    updatedBy: '',
    version: '', // 数据库版本
  });

  /** 根据 dbType 渲染对应的模块信息组件 */
  const moduleInfoComponent = {
    [DBTypes.MYSQL]: MySql,
    [DBTypes.SQLSERVER]: SqlServer,
    [DBTypes.TENDBCLUSTER]: TendbCluster,
  } as Record<DBTypes, any>;

  /** 获取模块部署信息 */
  const { loading, run: fetchModuleConfig } = useRequest(getLevelConfig, {
    manual: true,
    onSuccess(result) {
      // 通过 ref 调用子组件的 parseConfig 方法并获取返回值
      const updates = moduleInfoRef.value?.parseConfig(result.conf_items) || {};
      Object.assign(moduleInfo, updates);

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

  watch(
    () => treeNode,
    (node, old) => {
      if (node && node.value && node.value.treeId !== old?.value?.treeId) {
        // 通过 ref 调用子组件的 getResetValues 方法并重置模块信息
        const resetValues = moduleInfoRef.value?.getResetValues() || {};
        Object.assign(moduleInfo, resetValues);

        moduleInfo.moduleId = node.value.id;
        moduleInfo.moduleName = node.value.name;

        buildRelatedClusters();

        if (Object.keys(moduleInfoComponent).includes(dbType.value)) {
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
    cloneModule({
      charset: moduleInfo.charset,
      confFile: moduleInfo.version,
      moduleId: moduleInfo.moduleId,
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
</script>

<style lang="less" scoped>
  .module-content {
    height: 100%;
  }

  .module-header-card {
    :deep(.db-card-content) {
      padding: 0;
    }
  }

  .module-header-actions {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .module-conf-tab {
    box-shadow: 0 2px 4px 0 rgba(25, 25, 41, 0.05);

    :deep(.bk-tab-content) {
      padding: 16px 16px 0;
      background: #fff;
    }
  }

  .module-operation-record {
    background: #fff;
    margin-top: 16px;
    padding-top: 16px;
    box-shadow: 0 2px 4px 0 rgba(25, 25, 41, 0.05);
  }
</style>

<style lang="less">
  .related-clusters-tooltip {
    padding: 8px 0;
    background-color: #333;
    color: #fff;
    border-radius: 2px;
    box-shadow: 0 2px 6px 0 rgba(0, 0, 0, 0.2);

    .related-clusters-list {
      max-height: 240px;
      overflow-y: auto;
      padding: 0 12px;
    }

    .related-cluster-item {
      line-height: 28px;
      color: #fff;
    }
  }
</style>
