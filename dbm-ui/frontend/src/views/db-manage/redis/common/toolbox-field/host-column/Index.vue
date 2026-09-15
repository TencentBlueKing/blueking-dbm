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
  <EditableColumn
    ref="editableTableColumn"
    :append-rules="rules"
    field="host.ip"
    fixed="left"
    :label="label"
    :loading="isLoading"
    :min-width="240"
    required>
    <template #headAppend>
      <BkButton
        text
        theme="primary"
        @click="handleShowSelector">
        <DbIcon type="batch-host-select" />
      </BkButton>
    </template>
    <EditableInput
      v-model="modelValue.ip"
      :disabled="disabled"
      :placeholder="placeholder || t('请输入IP')">
    </EditableInput>
    <HostSelector
      v-model="selectedList"
      v-model:is-show="isShowSelector"
      :cluster-types="clusterTypes"
      :data-source-map="dataSourceMap"
      :disable-select-method="disableSelectMethod"
      :tab-name-map="tabNameMap"
      @change="handleHostSelectChange" />
  </EditableColumn>
</template>

<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { getGlobalMachine } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import HostSelector, {
    type HostModel,
    type HostSelectorValues,
    type ISupportHostType,
  } from '@components/host-selector/Index.vue';

  type HostSelectorProps = ComponentProps<typeof HostSelector>;

  interface Props {
    clusterTypes: ISupportHostType[];
    dataSourceMap?: HostSelectorProps['dataSourceMap'];
    disabled?: boolean;
    disableSelectMethod?: HostSelectorProps['disableSelectMethod'];
    label: string;
    placeholder?: string;
    selected: {
      ip: string;
    }[];
    // 外部自定义 Tab 文案
    tabNameMap?: HostSelectorProps['tabNameMap'];
  }

  type Emits = (e: 'batch-edit', value: HostModel<ClusterTypes.REDIS>[]) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_host_id: number;
    ip: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('目标主机输入格式有误'),
      trigger: 'change',
      validator: (value: string) => ipv4.test(value),
    },
    {
      message: t('目标主机重复'),
      trigger: 'blur',
      validator: (value: string) => props.selected.filter((item) => item.ip === value).length < 2,
    },
    {
      message: t('目标主机不存在'),
      trigger: 'blur',
      validator: () => Boolean(modelValue.value.bk_host_id),
    },
  ];

  const isShowSelector = ref(false);
  const isLoading = ref(false);

  const selectedList = computed(
    () =>
      ({
        [props.clusterTypes[0]]: props.selected,
      }) as unknown as HostSelectorValues<ISupportHostType>,
  );

  watch(
    () => modelValue.value.ip,
    () => {
      if (!modelValue.value.bk_host_id && modelValue.value.ip) {
        isLoading.value = true;
        modelValue.value.bk_host_id = 0;
        getGlobalMachine({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          db_type: DBTypes.REDIS,
          ip: modelValue.value.ip,
        })
          .then((data) => {
            if (data.results.length > 0) {
              [modelValue.value] = data.results;
            }
          })
          .finally(() => {
            isLoading.value = false;
          });
      }
      if (!modelValue.value.ip) {
        modelValue.value.bk_host_id = 0;
      }
    },
    {
      immediate: true,
    },
  );

  const handleShowSelector = () => {
    isShowSelector.value = true;
  };

  const handleHostSelectChange = (data: HostSelectorValues<ISupportHostType>) => {
    // 本列固定为 Redis 主机语义，取值收敛为 RedisMachineModel
    const hostList = Object.values(data).flatMap((selectedList) => selectedList) as HostModel<ClusterTypes.REDIS>[];
    emits('batch-edit', hostList);
  };
</script>

<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
