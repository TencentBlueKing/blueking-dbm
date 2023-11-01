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
    class="spider-instance-selector"
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
          :cluster-id="clusterId"
          :get-table-list="getTableList"
          :get-topo-list="getTopoList"
          :last-values="lastValues"
          :role="role"
          :table-setting="tableSettings"
          :ticket-type="ticketType"
          @change="handleChange" />
      </template>
      <template #aside>
        <PreviewResult
          :get-table-list="getTableList"
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
          class="w-88"
          :disabled="isEmpty"
          theme="primary"
          @click="handleSubmit">
          {{ $t('确定') }}
        </BkButton>
      </span>
      <BkButton
        class="ml8 w-88"
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
    tendbcluster: IValue[],
  }

  export default {
    name: 'SpiderInstanceSelector',
  };
</script>
<script setup lang="ts" generic="T extends any">
  import { getResourceInstances } from '@services/clusters';
  import { queryClusters } from '@services/source/mysqlCluster';
  import type { ListBase } from '@services/types/common';

  import getSettings from '@components/instance-selector-new/common/tableSettings';

  import RenderManualInput from './components/ManualInputContent.vue';
  import PanelTab, {
    activePanelInjectionKey,
    defaultPanelList,
  } from './components/PanelTab.vue';
  import PreviewResult from './components/preview-result/PreviewResult.vue';
  import RenderTopo from './components/table-content/topo/Index.vue';

  export type TableSetting = ReturnType<typeof getSettings>;

  interface Props {
    isShow?: boolean;
    clusterId?: number;
    panelList?: { name: string; id: string, content?: Element }[],
    role?: string,
    selected?: InstanceSelectorValues,
    ticketType?: string,
    // eslint-disable-next-line vue/no-unused-properties
    getTopoList?: (params: Record<any, any>) => T[]
    // eslint-disable-next-line vue/no-unused-properties
    getTableList?: (params: Record<string, any>) => ListBase<T[]>
  }

  interface Emits {
    (e: 'update:isShow', value: boolean): void,
    (e: 'change', value: InstanceSelectorValues): void
  }

  const props = withDefaults(defineProps<Props>(), {
    isShow: false,
    clusterId: undefined,
    panelList: () => [...defaultPanelList],
    role: '',
    selected: undefined,
    ticketType: '',
    getTopoList: queryClusters as unknown as (params: Record<any, any>) => T[],
    getTableList: getResourceInstances as unknown as (params: Record<string, any>) => ListBase<T[]>,
  });

  const emits = defineEmits<Emits>();

  const panelTabActive = ref<'tendbcluster'|'manualInput'>('tendbcluster');
  const lastValues = reactive<InstanceSelectorValues>({
    tendbcluster: [],
  });

  const comMap = {
    tendbcluster: RenderTopo,
    manualInput: RenderManualInput,
  };

  const tableSettings = getSettings(props.role);

  const isEmpty = computed(() => !Object.values(lastValues).some(values => values.length > 0));
  const renderCom = computed(() => comMap[panelTabActive.value as keyof typeof comMap]);

  provide(activePanelInjectionKey, panelTabActive);

  watch(() => props.isShow, (show) => {
    if (show && props.selected) {
      Object.assign(lastValues, props.selected);
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
  .spider-instance-selector {
    display: block;
    width: 80%;
    max-width: 1600px;
    min-width: 1200px;

    .bk-modal-header {
      display: none;
    }

    .bk-modal-content {
      padding: 0 !important;
      overflow-y: hidden !important;
    }
  }
</style>
