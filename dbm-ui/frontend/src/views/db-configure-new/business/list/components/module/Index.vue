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
        <BkForm class="module-info-form">
          <div class="module-info-form-row">
            <BkFormItem :label="t('模块名称：')">
              {{ moduleInfo.moduleName || '--' }}
            </BkFormItem>
            <BkFormItem :label="t('模块 ID：')">
              {{ moduleInfo.moduleId || '--' }}
            </BkFormItem>
          </div>
          <div class="module-info-form-row">
            <BkFormItem :label="t('存储层版本：')">
              {{ moduleInfo.version || '--' }}
            </BkFormItem>
            <BkFormItem :label="t('字符集：')">
              {{ moduleInfo.charset || '--' }}
            </BkFormItem>
          </div>
          <div class="module-info-form-row">
            <BkFormItem :label="t('最近更新人：')">
              {{ moduleInfo.updatedBy || '--' }}
            </BkFormItem>
            <BkFormItem :label="t('更新时间：')">
              {{ moduleInfo.updatedAt || '--' }}
            </BkFormItem>
          </div>
          <div class="module-info-form-row">
            <BkFormItem :label="t('关联集群：')">
              <span class="related-clusters">
                <span
                  v-overflow-tips="{ content: moduleInfo.relatedClusters, placement: 'top' }"
                  class="related-clusters-text text-overflow">
                  {{ moduleInfo.relatedClusters || '--' }}
                </span>
                <template v-if="moduleInfo.relatedClusterCount > 0">
                  <span class="related-clusters-count">
                    {{ t('共') }} {{ moduleInfo.relatedClusterCount }} {{ t('个') }}
                  </span>
                  <DbIcon
                    class="related-clusters-copy"
                    type="bk-dbm-icon db-icon-copy"
                    @click="handleCopyClusters" />
                </template>
              </span>
            </BkFormItem>
          </div>
        </BkForm>
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
          <!-- 参数配置子 tabs -->
          <ConfTab
            class="module-conf-tab mt-16"
            :db-module-id="moduleInfo.moduleId">
            <template #default="{ tab }">
              <BkAlert
                class="mb-16"
                closable
                theme="info"
                :title="t('模块配置参数说明')" />
              <ParamTable
                :cluster-type="clusterType"
                :conf-type="tab.conf_type"
                level-name="module"
                :level-value="moduleInfo.moduleId"
                selectable
                :version="moduleInfo.version" />
            </template>
          </ConfTab>
        </BkTabPanel>
        <BkTabPanel
          :label="t('操作记录')"
          name="operationRecord"
          render-directive="if">
          <div class="module-operation-record">
            <OperationRecord />
          </div>
        </BkTabPanel>
      </BkTab>
    </BkLoading>
  </div>
</template>

<script setup lang="ts">
  import type { ComputedRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import { deleteModuleConfig, getLevelConfig } from '@services/source/configs';

  import { clusterTypeInfos, ClusterTypes, ConfLevels, DBTypes } from '@common/const';

  import type { TreeData, TreeState } from '@views/db-configure-new/common/types';
  import ConfTab from '@views/db-configure-new/components/ConfTab.vue';
  import ParamTable from '@views/db-configure-new/components/ParamTable.vue';
  import { useTreeData } from '@views/db-configure-new/hooks/useTreeData';

  import { messageSuccess } from '@utils';

  import OperationRecord from '../biz/components/OperationRecord.vue';

  const route = useRoute();
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
    updatedAt: '',
    updatedBy: '',
    version: '',
  });

  /** 顶部 tabs: 参数配置 / 操作记录 */
  const activeTopTab = ref('paramConfig');

  /** 获取模块部署信息 */
  const { loading, run: fetchModuleConfig } = useRequest(getLevelConfig, {
    manual: true,
    onSuccess(result) {
      result.conf_items.forEach((item) => {
        if (item.conf_name === 'db_version') {
          moduleInfo.version = item.conf_value ?? '';
        } else if (item.conf_name === 'charset') {
          moduleInfo.charset = item.conf_value ?? '';
        }
      });
      moduleInfo.updatedBy = result.updated_by || '';
      moduleInfo.updatedAt = result.updated_at || '';
    },
  });

  /** 构建关联集群信息 */
  const buildRelatedClusters = () => {
    if (!treeNode?.value) return;

    const children = treeNode.value.children || [];
    const clusterNodes = children.filter((child) => child.levelType === ConfLevels.CLUSTER);
    moduleInfo.relatedClusterCount = clusterNodes.length;
    moduleInfo.relatedClusters = clusterNodes.map((node) => node.name).join(', ');
  };

  /** 监听树节点变化 */
  watch(
    () => treeNode,
    (node, old) => {
      if (node && node.value && node.value.treeId !== old?.value?.treeId) {
        moduleInfo.version = '';
        moduleInfo.charset = '';
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

  /** 复制关联集群 */
  const handleCopyClusters = () => {
    if (moduleInfo.relatedClusters) {
      navigator.clipboard.writeText(moduleInfo.relatedClusters);
    }
  };

  /** 克隆模块 */
  const handleCloneModule = () => {
    createModule({
      clusterType: clusterType.value,
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

  .module-info-form {
    display: flex;
    flex-direction: column;
    padding: 16px 24px;
  }

  .module-info-form-row {
    display: flex;
    width: 100%;

    :deep(.bk-form-item) {
      flex: 1;
      margin-bottom: 0;
    }
  }

  .related-clusters {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    max-width: 100%;
  }

  .related-clusters-text {
    max-width: 400px;
  }

  .related-clusters-count {
    flex-shrink: 0;
    font-size: 12px;
    color: #ff9c01;
    white-space: nowrap;
  }

  .related-clusters-copy {
    flex-shrink: 0;
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
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
