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
    class="dbm-mongo-host-selector"
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
        <MongoHostTable
          :disable-select-method="disableSelectMethod"
          :fetch-params="fetchParams"
          :selected="lastValues"
          :single="single"
          @selection="handleTableSelection" />
      </template>
      <template #aside>
        <PreviewResult
          :list="lastValues"
          @change="handlePreviewChange" />
      </template>
    </BkResizeLayout>
    <template #footer>
      <span
        v-bk-tooltips="{
          disabled: lastValues.length > 0,
          content: t('请选择主机'),
        }">
        <BkButton
          v-test="{ type: 'button', value: 'instanceSelectorConfirm' }"
          class="w-88"
          :disabled="lastValues.length === 0"
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

<script lang="ts">
  export type { DisableSelectMethod, MongoHostFetchParams, MongoHostRow } from './types';
</script>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import PreviewResult from './components/preview-result/Index.vue';
  import MongoHostTable from './components/Table.vue';
  import { type DisableSelectMethod, type MongoHostFetchParams, type MongoHostRow } from './types';

  export interface Props {
    disableSelectMethod?: DisableSelectMethod;
    fetchParams?: MongoHostFetchParams;
    single?: boolean;
  }

  type Emits = {
    (e: 'change', value: MongoHostRow[]): void;
    (e: 'cancel'): void;
  };

  defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<MongoHostRow[]>({
    required: true,
  });
  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const lastValues = ref<MongoHostRow[]>([]);

  // 打开时以 modelValue 为种子；关闭不做额外请求
  watch(
    isShow,
    (show) => {
      if (show) {
        lastValues.value = _.cloneDeep(modelValue.value);
      }
    },
    {
      immediate: true,
    },
  );

  const handleTableSelection = (list: MongoHostRow[]) => {
    lastValues.value = list;
  };

  const handlePreviewChange = (list: MongoHostRow[]) => {
    lastValues.value = list;
  };

  const handleConfirm = () => {
    emits('change', lastValues.value);
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
  .dbm-mongo-host-selector {
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
