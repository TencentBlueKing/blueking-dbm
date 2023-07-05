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
    :quick-close="false"
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
          :panel-list="panelList" />
        <Component
          :is="renderCom"
          :key="panelTabActive"
          :db-type="dbType"
          :last-values="lastValues"
          :role="role"
          :table-settings="defaultSettings"
          @change="handleChange" />
      </template>
      <template #aside>
        <PreviewResult
          :last-values="lastValues"
          table-key="ip"
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
  import type { ChoosedItem } from './components/RenderRedisHost.vue';

  export type InstanceSelectorValues = {
    idleHosts: ChoosedItem[],
  }

  export default {
    name: 'InstanceSelector',
  };
</script>
<script setup lang="ts">
  import getSettings from './common/tableSettings';
  import PanelTab, { activePanelInjectionKey, defaultPanelList, type PanelTypes } from './components/PanelTab.vue';
  import PreviewResult from './components/PreviewResult.vue';
  import RenderManualInput from './components/RenderManualInput.vue';
  import RenderRedis from './components/RenderRedis.vue';

  interface Props {
    isShow?: boolean;
    panelList?: Array<PanelTypes>,
    role?: string,
    values?: InstanceSelectorValues,
    dbType?: string,
    activeTab?: PanelTypes
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
    dbType: 'redis',
    activeTab: 'idleHosts',
  });
  const emits = defineEmits<Emits>();

  const defaultSettings = getSettings(props.role);
  const panelTabActive = ref<PanelTypes>(props.activeTab);

  const lastValues = reactive<InstanceSelectorValues>({
    idleHosts: [],
  });
  const isEmpty = computed(() => !Object.values(lastValues).some(values => values.length > 0));
  provide(activePanelInjectionKey, panelTabActive);

  const comMap = {
    idleHosts: RenderRedis,
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
