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
  <BkDialog
    class="dbm-cluster-selector"
    :close-icon="false"
    :draggable="false"
    :esc-close="false"
    :is-show="isShow"
    :quick-close="false"
    width="80%"
    @closed="handleClose">
    <BkResizeLayout
      :border="false"
      collapsible
      initial-divide="320px"
      :max="360"
      :min="320"
      placement="right">
      <template #main>
        <PanelTab
          v-model="currentPanelTab"
          :cluster-types="clusterTypes"
          :is-empty="isEmpty"
          :name-map="nameMap"
          :unique-panel-settings="localUniquePanelSettings" />
        <Table
          :key="currentPanelTab"
          :cluster-type="currentPanelTab"
          :data-source-map="dataSourceMap"
          :disable-select-method="disableSelectMethod"
          :selected="currentTableData"
          :single="single"
          :support-offline-data="supportOfflineData"
          @selection="handleSelection" />
      </template>
      <template #aside>
        <PreviewResult
          :cluster-types="clusterTypes"
          :last-values="lastValues"
          :name-map="nameMap"
          @change="handlePreviewChange" />
      </template>
    </BkResizeLayout>
    <template #footer>
      <span class="mr-24">
        <slot
          v-if="slots.submitTips"
          :cluster-list="selectedClusterList"
          name="submitTips" />
      </span>
      <span v-bk-tooltips="submitButtonDisabledInfo.tooltips">
        <BkButton
          v-test="{ type: 'button', value: 'clusterSelectorConfirm' }"
          class="w-88"
          :disabled="submitButtonDisabledInfo.disabled || isEmpty"
          :loading="relatedClustersLoading"
          theme="primary"
          @click="handleBeforeConfirm">
          {{ t('确定') }}
        </BkButton>
      </span>
      <BkButton
        class="ml-8 w-88"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script lang="ts">
  import _ from 'lodash';
  import type { UnwrapRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import useClusterList from '@views/db-manage/hooks/useClusterList';
  import useClusterRelatedClusterList, {
    type ISurpportClusterTypes as ISurpportRelatedClusterTypes,
  } from '@views/db-manage/hooks/useClusterRelatedClusterList';

  import PanelTab from './components/PanelTab.vue';
  import PreviewResult from './components/preview-result/Index.vue';
  import Table from './components/table/Index.vue';
  import { type ClusterModel, type ISupportClusterType } from './types';

  export { type ClusterModel, type ISupportClusterType };
</script>
<script setup lang="ts" generic="T extends ISupportClusterType">
  export interface Props<C extends ISupportClusterType> {
    addRelatedCluster?: boolean;
    clusterTypes: C[];
    dataSourceMap?: {
      [key in C]?: ReturnType<typeof useClusterList<key>>;
    };
    disableSelectMethod?: (data: ClusterModel<C>) => boolean | string;
    disableSubmitMethod?: (list: string[]) => string | boolean;
    nameMap?: {
      [key in C]?: string;
    };
    relatedClusterDataSourceMap?: {
      [key in ISurpportRelatedClusterTypes]?: ReturnType<typeof useClusterRelatedClusterList<key>>;
    };
    repeatable?: boolean;
    single?: boolean;
    supportOfflineData?: boolean;
    uniquePanelSettings?: boolean | ComponentProps<typeof PanelTab>['uniquePanelSettings'];
  }

  type Emits = {
    (e: 'change', value: UnwrapRef<typeof modelValue>): void;
    (e: 'cancel'): void;
  };

  const props = defineProps<Props<T>>();
  const emits = defineEmits<Emits>();
  const slots = defineSlots<{
    submitTips?: (params: { clusterList: string[] }) => VNode;
  }>();

  const modelValue = defineModel<{ [key in T]: ClusterModel<T>[] }>({
    required: true,
  });
  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const currentPanelTab = ref(props.clusterTypes[0]);
  const lastValues = ref({} as UnwrapRef<typeof modelValue>);
  const relatedClustersLoading = ref(false);

  const currentTableData = computed(() => lastValues.value[currentPanelTab.value] || []);
  const isEmpty = computed(() =>
    Object.values<ClusterModel<T>[]>(lastValues.value).every((values) => values.length === 0),
  );

  const selectedClusterList = computed(() =>
    Object.values<ClusterModel<T>[]>(lastValues.value).flatMap((selectedItem) =>
      selectedItem.map((clusterItem) => clusterItem.master_domain),
    ),
  );

  const submitButtonDisabledInfo = computed(() => {
    const info = {
      disabled: false,
      tooltips: {
        content: '',
        disabled: true,
      },
    };

    if (isEmpty.value) {
      info.disabled = true;
      info.tooltips.disabled = false;
      info.tooltips.content = t('请选择集群');
      return info;
    }

    const checkValue = props.disableSubmitMethod ? props.disableSubmitMethod(selectedClusterList.value) : false;
    if (checkValue) {
      info.disabled = true;
      info.tooltips.disabled = false;
      info.tooltips.content = _.isString(checkValue) ? checkValue : t('无法保存');
    }
    return info;
  });

  const localUniquePanelSettings = computed(() =>
    _.isBoolean(props.uniquePanelSettings) ? { enable: props.uniquePanelSettings } : props.uniquePanelSettings,
  );

  watch(isShow, () => {
    lastValues.value = _.cloneDeep(modelValue.value);
  });

  const handleSelection = (list: ClusterModel<T>[]) => {
    const lastValuesMemo = { ...lastValues.value };
    lastValues.value = Object.assign(lastValuesMemo, {
      [currentPanelTab.value]: list,
    });
  };

  const handlePreviewChange = (values: UnwrapRef<typeof modelValue>) => {
    lastValues.value = values;
  };

  const handleBeforeConfirm = () => {
    if (props.addRelatedCluster) {
      const promiseList = Object.entries<ClusterModel<T>[]>(lastValues.value).reduce<
        Promise<UnwrapRef<typeof modelValue>>[]
      >((prev, [key, clusters]) => {
        const api =
          props.relatedClusterDataSourceMap?.[key as ISurpportRelatedClusterTypes] ||
          useClusterRelatedClusterList(key as ISurpportRelatedClusterTypes);
        if (api && props.clusterTypes.includes(key as T)) {
          // 只查询新增的集群信息
          const selectedClusterMemo = Object.fromEntries(
            modelValue.value[key as T].map((item) => [item.master_domain, true]),
          );
          const clusterIds = clusters
            .map((clusterItem) => clusterItem.id)
            .filter((clusterId) => !selectedClusterMemo[clusterId]);

          return prev.concat(
            api({
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              cluster_ids: clusterIds,
            }).then((relatedClusters) => {
              const keySet = new Set<string>();
              const relatedClusterMap = relatedClusters.reduce<Record<string, string>>((acc, item) => {
                const key = _.sortBy([item.cluster_info, ...item.related_clusters], (cluster) => cluster.id)
                  .map((cluster) => cluster.id)
                  .join(',');
                const isExits = [item.cluster_info, ...item.related_clusters].some(
                  (infoItem) => selectedClusterMemo[infoItem.master_domain],
                );
                if (isExits) {
                  keySet.add(key);
                }

                return Object.assign(acc, {
                  [item.cluster_info.master_domain]: key,
                });
              }, {});

              // 自动去除重复的关联集群信息
              const newValue = clusters.filter((clusterItem) => {
                const clusterKey = relatedClusterMap[clusterItem.master_domain];
                if (clusterKey && !keySet.has(clusterKey)) {
                  keySet.add(clusterKey);
                  return true;
                }
                return false;
              });
              return { [key]: newValue } as UnwrapRef<typeof modelValue>;
            }),
          );
        }
        return prev;
      }, []);

      relatedClustersLoading.value = true;
      Promise.all(promiseList)
        .then((result) => {
          const resultObject = result.reduce(
            (acc, obj) => {
              return Object.assign(acc, obj);
            },
            {} as UnwrapRef<typeof modelValue>,
          );
          handleConfirm(resultObject);
        })
        .finally(() => {
          relatedClustersLoading.value = false;
        });
    } else {
      handleConfirm();
    }
  };

  const handleConfirm = (other?: UnwrapRef<typeof modelValue>) => {
    const result = Object.assign(lastValues.value, other);
    if (!props.repeatable) {
      modelValue.value = result;
    }
    emits('change', result);
    handleClose();
  };

  const handleCancel = () => {
    emits('cancel');
    handleClose();
  };

  const handleClose = () => {
    isShow.value = false;
  };
</script>

<style lang="less">
  .dbm-cluster-selector {
    display: block;
    width: 80%;
    max-width: 1600px;
    min-width: 1200px;

    .bk-modal-header {
      display: none;
    }

    .bk-dialog-content {
      padding: 0;
      margin: 0;
    }
  }
</style>
