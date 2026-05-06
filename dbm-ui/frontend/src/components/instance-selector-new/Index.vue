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
    class="dbm-instance-selector"
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
          :unique-panel-settings="uniquePanelSettings" />
        <Table
          :key="currentPanelTab"
          :cluster-type="currentPanelTab"
          :data-source-map="dataSourceMap"
          :disable-select-method="disableSelectMethod"
          :selected="currentTableData"
          :single="single"
          @selection="handleSelection" />
      </template>
      <template #aside>
        <PreviewResult
          :cluster-types="clusterTypes"
          :last-values="lastValues"
          @change="handlePreviewChange" />
      </template>
    </BkResizeLayout>
    <template #footer>
      <span
        v-bk-tooltips="{
          disabled: !isEmpty,
          content: t('请选择实例'),
        }">
        <BkButton
          v-test="{ type: 'button', value: 'instanceSelectorConfirm' }"
          class="w-88"
          :disabled="isEmpty"
          theme="primary"
          @click="handleConfirm">
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

<script setup lang="ts" generic="T extends ISupportClusterType">
  import _ from 'lodash';
  import type { UnwrapRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import useClusterInstaceList from '@views/db-manage/hooks/useClusterInstaceList';

  import PanelTab from './components/PanelTab.vue';
  import PreviewResult from './components/preview-result/Index.vue';
  import Table from './components/Table.vue';
  import { type InstanceModel, type ISupportClusterType } from './types';

  export interface Props<C extends ISupportClusterType> {
    clusterTypes: C[];
    dataSourceMap?: {
      [key in C]?: ReturnType<typeof useClusterInstaceList<key>>;
    };
    disableSelectMethod?: (data: InstanceModel<C>) => boolean | string;
    repeatable?: boolean;
    single?: boolean;
    uniquePanelSettings?: ComponentProps<typeof PanelTab>['uniquePanelSettings'];
  }

  type Emits = {
    (e: 'change', value: UnwrapRef<typeof modelValue>): void;
    (e: 'cancel'): void;
  };

  const props = defineProps<Props<T>>();
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{ [key in T]: InstanceModel<T>[] }>({
    required: true,
  });
  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const currentPanelTab = ref(props.clusterTypes[0]);
  const lastValues = ref({} as UnwrapRef<typeof modelValue>);

  const currentTableData = computed(() => lastValues.value[currentPanelTab.value] || []);

  const isEmpty = computed(() =>
    Object.values<InstanceModel<T>[]>(lastValues.value).every((values) => values.length === 0),
  );

  watch(isShow, () => {
    lastValues.value = _.cloneDeep(modelValue.value);
  });

  const handleSelection = (list: InstanceModel<T>[]) => {
    const lastValuesMemo = { ...lastValues.value };
    lastValues.value = Object.assign(lastValuesMemo, {
      [currentPanelTab.value]: list,
    });
  };

  const handlePreviewChange = (values: UnwrapRef<typeof modelValue>) => {
    lastValues.value = values;
  };

  const handleConfirm = () => {
    if (!props.repeatable) {
      modelValue.value = lastValues.value;
    }
    emits('change', lastValues.value as UnwrapRef<typeof modelValue>);
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
  .dbm-instance-selector {
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
