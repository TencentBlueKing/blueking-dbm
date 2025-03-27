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
    class="dbm-global-instance-selector"
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
        <PanelTab v-model="activeTab" />
        <BkResizeLayout
          :border="false"
          collapsible
          initial-divide="340px"
          :max="420"
          :min="320">
          <template #aside>
            <Component
              :is="comMap[activeTab]"
              :params="afferentParams"
              @change="handleChangeParams" />
          </template>
          <template #main>
            <RenderTable
              :params="localParams"
              :selected="selected"
              @change="handleChange" />
          </template>
        </BkResizeLayout>
      </template>
      <template #aside>
        <PreviewResult
          :selected="selected"
          @change="handleChange" />
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

  import { clusterTypeInfos, ClusterTypes, DBTypes } from '@common/const';

  import ManualInput from './components/ManualInput.vue';
  import PanelTab from './components/PanelTab.vue';
  import PreviewResult from './components/preview-result/Index.vue';
  import RenderTable, { type IValue, type Parameters } from './components/RenderTable.vue';
  import TopoTree from './components/TopoTree.vue';

  export type InstanceItem = IValue;

  interface Props {
    clusterType: ClusterTypes[];
    role?: string;
  }

  type Emits = (e: 'change', data: IValue[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    required: true,
  });

  const selected = defineModel<IValue[]>('selected', {
    required: true,
  });

  const { t } = useI18n();

  const comMap = {
    ManualInput,
    TopoTree,
  };

  const activeTab = ref<'TopoTree' | 'ManualInput'>('TopoTree');
  const localParams = ref<Parameters>({
    db_type: DBTypes.MYSQL,
  });

  /**
   * 传入的默认参数
   */
  const afferentParams = computed(() => ({
    cluster_type: props.clusterType.join(','),
    db_type: clusterTypeInfos[props.clusterType[0] as keyof typeof clusterTypeInfos]?.dbType,
    role: props.role,
  }));

  watch(isShow, () => {
    if (isShow.value) {
      localParams.value = {
        ...afferentParams.value,
      };
    }
  });

  const handleChangeParams = (params: { bk_biz_id?: number; db_module_id?: number; instance?: string }) => {
    localParams.value = {
      ...afferentParams.value,
      ...params,
    };
  };

  const handleChange = (data: IValue[]) => {
    selected.value = data;
  };

  const handleClose = () => {
    isShow.value = false;
  };

  const handleSubmit = () => {
    emits('change', selected.value);
    handleClose();
  };
</script>
<style lang="less">
  .dbm-global-instance-selector {
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
