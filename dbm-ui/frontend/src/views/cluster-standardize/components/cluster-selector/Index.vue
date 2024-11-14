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
          :db-type="dbType" />
        <Component
          :is="ClusterSelect"
          :key="panelTabActive"
          :active-panel-id="panelTabActive"
          :last-values="lastValues"
          @change="handleChange" />
      </template>
      <template #aside>
        <PreviewResult
          :active-panel-id="panelTabActive"
          :last-values="lastValues"
          @change="handleChange" />
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
<script lang="ts">
  import type { ClusterInfo } from '@services/types';

  import { ClusterTypes, DBTypes } from '@common/const';

  interface SelectedMap {
    [DBTypes.MYSQL]: {
      [ClusterTypes.TENDBHA]?: ClusterInfo[];
      [ClusterTypes.TENDBSINGLE]?: ClusterInfo[];
    };
    [DBTypes.TENDBCLUSTER]: {
      [ClusterTypes.TENDBCLUSTER]?: ClusterInfo[];
    };
  }
</script>
<script setup lang="ts" generic="T extends keyof SelectedMap">
  import { useI18n } from 'vue-i18n';

  import ClusterSelect from './components/cluster-select/Index.vue';
  import PanelTab from './components/common/PanelTab.vue';
  // import ManualInput from './components/manual-input/Index.vue';
  import PreviewResult from './components/preview-result/Index.vue';

  interface Props {
    dbType: T;
    selected: SelectedMap[T];
  }

  interface Emits {
    (e: 'change', value: Props['selected']): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const panelTabActive = ref();
  const lastValues = reactive<Props['selected']>({});

  // const renderCom = computed(
  //   () => {
  //     if (panelTabActive.value === 'manual') {
  //       return ManualInput;
  //     }
  //     return ClusterSelect;
  //   }
  // );
  const isEmpty = computed(() => Object.values(lastValues).every((values) => values.length < 1));

  watch(
    isShow,
    () => {
      if (!isShow.value) {
        return;
      }
      if (props.selected) {
        Object.assign(lastValues, props.selected);
        for (const [key, values] of Object.entries(props.selected)) {
          if (values.length > 0) {
            panelTabActive.value = key;
            break;
          }
        }
      }
    },
    {
      immediate: true,
    },
  );

  watch(panelTabActive, (_, oldValue) => {
    Object.assign(lastValues, {
      [oldValue]: [],
    });
  });

  const handleChange = (values: Record<string, ClusterInfo[]>) => {
    Object.assign(lastValues, values);
  };

  const handleSubmit = () => {
    emits('change', lastValues);
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
