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
    class="dbm-proxy-selector"
    :close-icon="false"
    :draggable="false"
    :esc-close="false"
    :is-show="isShow"
    :quick-close="false">
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
          :panel-list="panelList" />
        <Component
          :is="renderCom"
          :key="panelTabActive"
          :last-values="lastValues"
          :role="role"
          :table-settings="tableSettings"
          @change="handleChange" />
      </template>
      <template #aside>
        <PreviewResult
          :last-values="lastValues"
          @change="handleChange" />
      </template>
    </BkResizeLayout>
    <template #footer>
      <span
        v-bk-tooltips="{
          content: $t('请选择实例'),
          disabled: !isEmpty
        }"
        class="inline-block">
        <BkButton
          class="w88"
          :disabled="isEmpty"
          theme="primary"
          @click="handleSubmit">
          {{ $t('确定') }}
        </BkButton>
      </span>
      <BkButton
        class="ml8 w88"
        @click="handleClose">
        {{ $t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script lang="ts">
  import type { IValue, MySQLClusterTypes } from './common/types';

  export type InstanceSelectorValue = IValue
  export type SupportClusterTypes = MySQLClusterTypes
  export type InstanceSelectorValues = {
    tendbha: IValue[],
    tendbsingle: IValue[],
  }

  export default {
    name: 'InstanceSelector',
  };
</script>
<script setup lang="ts">
  import {
    ref,
  } from 'vue';

  import getSettings from './common/tableSettings';
  import PanelTab, { activePanelInjectionKey, defaultPanelList, type PanelTypes } from './components/PanelTab.vue';
  import PreviewResult from './components/PreviewResult.vue';
  import RenderManualInput from './components/RenderManualInput.vue';
  import RenderTopo from './components/RenderTopo.vue';

  interface Props {
    isShow?: boolean;
    panelList?: Array<PanelTypes>,
    role?: string,
    values?: InstanceSelectorValues
  }

  interface Emits {
    (e: 'update:isShow', value: boolean): void,
    (e: 'change', value: InstanceSelectorValues): void
  }

  const props = withDefaults(defineProps<Props>(), {
    isShow: false,
    panelList: () => [...defaultPanelList],
    role: '',
    values: undefined,
  });
  const emits = defineEmits<Emits>();

  const tableSettings = getSettings(props.role);
  const panelTabActive = ref<PanelTypes>('tendbha');
  // const lastValue = shallowRef<IValue []>([]);
  const lastValues = reactive<InstanceSelectorValues>({
    tendbha: [],
    tendbsingle: [],
  });
  const isEmpty = computed(() => !Object.values(lastValues).some(values => values.length > 0));
  provide(activePanelInjectionKey, panelTabActive);

  const comMap = {
    tendbha: RenderTopo,
    tendbsingle: RenderTopo,
    manualInput: RenderManualInput,
  };

  const renderCom = computed(() => comMap[panelTabActive.value as keyof typeof comMap]);

  watch(() => props.isShow, (show) => {
    if (show && props.values) {
      Object.assign(lastValues, props.values);
    }
  });

  const handleChange = (values: InstanceSelectorValues) => {
    Object.assign(lastValues, values);
  };

  const handleSubmit = () => {
    emits('change', lastValues);
    handleClose();
  };

  const handleClose = () => {
    emits('update:isShow', false);
    lastValues.tendbha = [];
    lastValues.tendbsingle = [];
  };
</script>
<style lang="less">
  .dbm-proxy-selector {
    display: block;
    width: 80%;
    max-width: 1600px;
    min-width: 1200px;

    .bk-modal-header {
      display: none;
    }

    .bk-modal-content {
      padding: 0 !important;
    }
  }
</style>
