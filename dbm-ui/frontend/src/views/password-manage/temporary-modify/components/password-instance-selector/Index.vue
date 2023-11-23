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
    class="password-instance-selector"
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
          :last-values="lastValues"
          :panel-tab-active="panelTabActive"
          :role="role"
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
          content: t('请选择实例'),
          disabled: !isEmpty
        }"
        class="inline-block">
        <BkButton
          class="w-88"
          :disabled="isEmpty"
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

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import {
    defaultPanelList,
    type InstanceSelectorValues,
    type PanelTypes,
  } from './common/types';
  import PanelTab from './components/PanelTab.vue';
  import PreviewResult from './components/PreviewResult.vue';
  import RenderManualInput from './components/RenderManualInput.vue';
  import RenderTopo from './components/RenderTopo.vue';

  interface Props {
    role?: string,
    values?: InstanceSelectorValues
  }

  interface Emits {
    (e: 'change', value: InstanceSelectorValues): void
  }

  const props = withDefaults(defineProps<Props>(), {
    role: '',
    values: undefined,
  });
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>({
    required: true,
    default: false,
  });

  const { t } = useI18n();

  const comMap = {
    tendbha: RenderTopo,
    tendbsingle: RenderTopo,
    tendbcluster: RenderTopo,
    manualInput: RenderManualInput,
  };

  const panelTabActive = ref<PanelTypes>(defaultPanelList[0]);
  const panelList = ref([...defaultPanelList]);
  const lastValues = reactive<InstanceSelectorValues>({
    tendbha: [],
    tendbsingle: [],
    tendbcluster: [],
  });

  const isEmpty = computed(() => !Object.values(lastValues).some(values => values.length > 0));


  const renderCom = computed(() => comMap[panelTabActive.value as keyof typeof comMap]);

  watch(() => isShow, (newVal) => {
    if (newVal && props.values) {
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
    isShow.value = false;
    lastValues.tendbha = [];
    lastValues.tendbsingle = [];
    lastValues.tendbcluster = [];
  };
</script>

<style lang="less">
  .password-instance-selector {
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
