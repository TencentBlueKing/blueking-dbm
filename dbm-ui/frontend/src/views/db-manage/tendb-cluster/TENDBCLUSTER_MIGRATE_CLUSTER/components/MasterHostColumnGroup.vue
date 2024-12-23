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
  <Column
    :append-rules="rules"
    field="oldMaster.ip"
    fixed="left"
    :label="t('目标主库主机')"
    :loading="loading"
    :min-width="150"
    required>
    <template #headAppend>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-host-select"
        @click="handleShowSelector">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <Input
      v-model="modelValue.ip"
      :placeholder="t('请输入IP')"
      @change="handleInputChange" />
  </Column>
  <Column
    :label="t('主库主机关联实例')"
    :loading="loading"
    :min-width="150">
    <div
      v-if="modelValue.related_instances.length"
      class="table-cell">
      <p
        v-for="item in modelValue.related_instances"
        :key="item">
        {{ item }}
      </p>
    </div>
    <Block
      v-else
      :placeholder="t('自动生成')" />
  </Column>
  <InstanceSelector
    v-model:is-show="showSelector"
    :cluster-types="['TendbClusterHost']"
    :selected="selectedHosts"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkInstance } from '@services/source/dbbase';

  import { ipv4 } from '@common/regex';

  import { Block, Column, Input } from '@components/editable-table/Index.vue';
  import InstanceSelector, { type InstanceSelectorValues, type IValue } from '@components/instance-selector/Index.vue';

  export type SelectorHost = IValue;

  export type InputedHost = ServiceReturnType<typeof checkInstance>[number];

  interface Props {
    selected: {
      bk_biz_id?: number;
      bk_cloud_id?: number;
      bk_host_id?: number;
      ip: string;
    }[];
  }

  interface Emits {
    (e: 'batch-edit', list: IValue[]): void;
    (e: 'change', data: InputedHost): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_biz_id?: number;
    bk_cloud_id?: number;
    bk_host_id?: number;
    ip: string;
    related_instances: string[];
  }>({
    default: () => ({
      ip: '',
      related_instances: [],
    }),
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const selectedHosts = computed<InstanceSelectorValues<IValue>>(() => ({
    TendbClusterHost: props.selected.map(
      (item) =>
        ({
          ip: item.ip,
        }) as IValue,
    ),
  }));

  const rules = [
    {
      validator: (value: string) => ipv4.test(value),
      message: t('IP 格式不符合IPv4标准'),
      trigger: 'change',
    },
    {
      validator: () => Boolean(modelValue.value.bk_host_id),
      message: t('目标主机不存在'),
      trigger: 'blur',
    },
  ];

  const { run: queryHost, loading } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      modelValue.value.bk_host_id = undefined;
      if (data.length) {
        const currentHost = data[0];
        const relatedInstances: string[] = [];
        data.forEach((item) => {
          relatedInstances.push(item.instance_address);
        });
        modelValue.value = {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: currentHost.bk_cloud_id,
          bk_host_id: currentHost.bk_host_id,
          ip: currentHost.ip,
          related_instances: relatedInstances,
        };
        emits('change', data[0]);
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    queryHost({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      instance_addresses: [value],
    });
  };

  const handleSelectorChange = (selected: InstanceSelectorValues<IValue>) => {
    emits('batch-edit', selected.TendbClusterHost);
  };
</script>
<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }

  .table-cell {
    padding: 0 8px;
  }
</style>
