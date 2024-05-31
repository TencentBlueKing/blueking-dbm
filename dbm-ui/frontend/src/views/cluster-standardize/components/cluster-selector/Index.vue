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
    class="cluster-selector"
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
          v-model="panelTabActive"
          @change="handleChangePanel" />
        <Component
          :is="renderCom"
          :key="panelTabActive"
          :checked="checkedMap"
          @change="handleChange" />
      </template>
      <template #aside>
        <PreviewResult
          :data="previewData"
          @clear="handleClear"
          @remove="handleRemove" />
      </template>
    </BkResizeLayout>
    <template #footer>
      <span
        v-bk-tooltips="{
          content: t('请选择集群'),
          disabled: !isEmpty,
        }"
        class="inline-block">
        <BkButton
          class="w-88"
          theme="primary"
          @click="handleSubmit">
          {{ t('确定') }}
        </BkButton>
      </span>
      <BkButton
        class="ml8 w-88"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts" generic="T extends TendbhaModel">
  import { t } from '@locales/index';

  import ClusterSelect from './components/cluster-select/Index.vue';
  import PanelTab, { PanelValues } from './components/common/PanelTab.vue';
  import ManualInput from './components/manual-input/Index.vue';
  import PreviewResult from './components/preview-result/Index.vue';

  import type TendbhaModel from '@/services/model/mysql/tendbha';

  interface Props {
    selected: Record<string, T>;
  }

  interface Emits {
    (e: 'change', value: T[]): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const panelTabActive = ref<string>(PanelValues.CLUSTER_SELECT);
  const checkedMap = shallowRef<Record<string, T>>({});
  const previewData = computed(() => Object.keys(checkedMap.value));
  const componentMap = {
    [PanelValues.CLUSTER_SELECT]: ClusterSelect,
    [PanelValues.MANUAL_INPUT]: ManualInput,
  };
  const renderCom = computed(() => componentMap[panelTabActive.value as PanelValues]);

  const isEmpty = computed(() => Object.keys(checkedMap.value).length < 1);

  watch(
    () => props.selected,
    (data) => {
      checkedMap.value = data;
    },
  );

  const handleChangePanel = (currentTab: string) => {
    panelTabActive.value = currentTab;
  };

  const handleChange = (values: Record<string, T>) => {
    checkedMap.value = values;
  };

  const handleRemove = (key: string) => {
    const lastCheckMap = { ...checkedMap.value };
    delete lastCheckMap[key];
    checkedMap.value = lastCheckMap;
  };

  const handleClear = () => {
    checkedMap.value = {};
  };

  const handleSubmit = () => {
    const result = Object.values(checkedMap.value).reduce((result, item) => {
      result.push({
        ...item,
      });
      return result;
    }, [] as T[]);
    emits('change', result);
    handleClose();
  };

  const handleClose = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .cluster-selector {
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
