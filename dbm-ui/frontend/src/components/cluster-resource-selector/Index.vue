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
    class="dbm-cluster-resource-selector"
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
          v-model="activeTab"
          :panel-list="panels" />
        <Component
          :is="config.mainComponent"
          v-model:selected="selected"
          :params="params" />
      </template>
      <template #aside>
        <Component
          :is="config.asideComponent"
          v-model:selected="selected" />
      </template>
    </BkResizeLayout>
    <template #footer>
      <BkButton
        class="w-88"
        :disabled="selected.length === 0"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="ml8 w-88"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { clusterTypeInfos, ClusterTypes } from '@common/const';

  import PanelTab from './components/common/PanelTab.vue';
  import InstanceManualInput from './components/instance/ManualInput.vue';
  import InstancePreviewResult, { type IValue } from './components/instance/PreviewResult.vue';
  import InstanceTopoSelect from './components/instance/TopoSelect.vue';

  export type Item = IValue;

  interface Props {
    clusterType: ClusterTypes[];
    role?: string;
    target?: 'instance';
  }

  type Emits = (e: 'change', data: IValue[]) => void;

  const props = withDefaults(defineProps<Props>(), {
    role: 'backend_master',
    target: 'instance',
  });

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    required: true,
  });

  const selected = defineModel<IValue[]>('selected', {
    required: true,
  });

  const { t } = useI18n();

  const activeTab = ref<string>('');

  const panelConfig = {
    instance: {
      asideComponent: InstancePreviewResult,
      id: 'instance',
      mainComponent: InstanceTopoSelect,
      name: t('选择实例'),
    },
    'instance-manual': {
      asideComponent: InstancePreviewResult,
      id: 'instance-manual',
      mainComponent: InstanceManualInput,
      name: t('手动输入'),
    },
    // 'machine': {
    //   id: 'topo-machine',
    //   name: t('选择主机'),
    // },
  };

  const panels = computed(() => [panelConfig[props.target], panelConfig[`${props.target}-manual`]]);

  const config = computed(() => panelConfig[activeTab.value as keyof typeof panelConfig]);

  const params = computed(() => ({
    cluster_type: props.clusterType.join(','),
    count_type: props.target,
    db_type: clusterTypeInfos[props.clusterType[0] as keyof typeof clusterTypeInfos]?.dbType,
    role: props.role,
  }));

  watch(isShow, () => {
    if (isShow.value) {
      activeTab.value = panels.value[0].id;
    }
  });

  const handleClose = () => {
    isShow.value = false;
  };

  const handleSubmit = () => {
    emits('change', selected.value);
    handleClose();
  };
</script>
<style lang="less">
  .dbm-cluster-resource-selector {
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
