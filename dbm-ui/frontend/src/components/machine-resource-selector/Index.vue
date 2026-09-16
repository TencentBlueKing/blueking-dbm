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
    class="dbm-machine-resource-selector"
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
          v-model="currentClusterType"
          :panel-list="configList" />
        <RenderTable
          v-model:selected="localSelected"
          :params="params" />
      </template>
      <template #aside>
        <PreviewResult v-model:selected="localSelected" />
      </template>
    </BkResizeLayout>
    <template #footer>
      <span
        v-bk-tooltips="{
          disabled: !isEmpty,
          content: t('请选择主机'),
        }">
        <BkButton
          class="w-88"
          :disabled="isEmpty"
          theme="primary"
          @click="handleSubmit">
          {{ t('确定') }}
        </BkButton>
      </span>
      <BkButton
        class="ml-8 w-88"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  import comFactory from './com-factory';
  import PanelTab from './components/PanelTab.vue';
  import PreviewResult from './components/PreviewResult.vue';
  import RenderTable, { type IValue } from './components/RenderTable.vue';

  export type IMachine = IValue;

  type SupportClusterTypes = keyof typeof comFactory;

  interface Props {
    clusterTypes: SupportClusterTypes[];
    role?: string;
  }

  type Emits = (e: 'change', data: IValue[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    required: true,
  });

  // 只作为回填数据源读取，选择结果通过 change 事件提交
  const selected = defineModel<IValue[]>('selected', {
    required: true,
  });

  const { t } = useI18n();

  const currentClusterType = ref<SupportClusterTypes>(ClusterTypes.TENDBHA);
  // 弹窗内的勾选走副本，点取消可丢弃
  const localSelected = shallowRef<IValue[]>([]);

  const configList = computed(() => props.clusterTypes.map((clusterType) => comFactory[clusterType]));

  const params = computed(() => ({
    ...comFactory[currentClusterType.value].params,
    instance_role: props.role,
  }));

  const isEmpty = computed(() => localSelected.value.length === 0);

  watch(isShow, () => {
    if (isShow.value) {
      currentClusterType.value = props.clusterTypes[0];
      localSelected.value = [...selected.value];
    }
  });

  const handleClose = () => {
    isShow.value = false;
  };

  const handleSubmit = () => {
    emits('change', localSelected.value);
    handleClose();
  };
</script>
<style lang="less">
  .dbm-machine-resource-selector {
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
