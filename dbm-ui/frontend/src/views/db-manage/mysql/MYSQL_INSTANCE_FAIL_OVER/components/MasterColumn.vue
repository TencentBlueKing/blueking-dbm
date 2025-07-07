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
    :append-rules="rules"
    field="master.instance_address"
    fixed="left"
    :label="t('故障主库实例')"
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
    <EditableInput
      v-model="modelValue.instance_address"
      :placeholder="t('请输入如: 192.168.10.2:1000')"
      @change="handleChange" />
  </EditableColumn>
  <InstanceSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.TENDBHA]"
    :selected="selectedInstances"
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkInstance } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipPort } from '@common/regex';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  export type SelectorHost = IValue;

  interface Props {
    selected: Array<typeof modelValue.value>;
  }

  type Emits = (e: 'batch-edit', list: IValue[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    instance_address: string;
    ip: string;
    port: number;
    related_clusters: {
      id: number;
      master_domain: string;
    }[];
    role: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const tabListConfig = {
    [ClusterTypes.TENDBHA]: [
      {
        id: ClusterTypes.TENDBHA,
        name: t('故障主库实例'),
        tableConfig: {
          firsrColumn: {
            field: 'instance_address',
            label: t('Master 实例'),
            role: 'backend_master',
          },
        },
      },
      {
        id: 'manualInput',
        name: t('手动输入'),
        tableConfig: {
          firsrColumn: {
            field: 'instance_address',
            label: t('Master 实例'),
            role: 'backend_master',
          },
        },
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  const showSelector = ref(false);
  const selectedInstances = computed<InstanceSelectorValues<IValue>>(() => ({
    [ClusterTypes.TENDBHA]: props.selected.map(
      (item) =>
        ({
          instance_address: item.instance_address,
        }) as IValue,
    ),
  }));

  const rules = [
    {
      message: t('目标实例输入格式有误'),
      trigger: 'blur',
      validator: (value: string) => !value || ipPort.test(value),
    },
    {
      message: t('目标实例不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.bk_host_id),
    },
    {
      message: t('非 Master 实例'),
      trigger: 'blur',
      validator: (value: string) => !value || modelValue.value.role === 'backend_master',
    },
  ];

  const { loading, run: queryHost } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      const [currentInstance] = data;
      if (currentInstance) {
        modelValue.value = {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: currentInstance.bk_cloud_id,
          bk_host_id: currentInstance.bk_host_id,
          instance_address: currentInstance.instance_address,
          ip: currentInstance.ip,
          port: currentInstance.port,
          related_clusters: currentInstance.related_clusters.map((item) => ({
            id: item.id,
            master_domain: item.master_domain,
          })),
          role: currentInstance.role,
        };
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleChange = (value: string) => {
    modelValue.value = {
      bk_biz_id: 0,
      bk_cloud_id: 0,
      bk_host_id: 0,
      instance_address: value,
      ip: '',
      port: 0,
      related_clusters: [],
      role: '',
    };
  };

  const handleSelectorChange = (selected: InstanceSelectorValues<IValue>) => {
    emits('batch-edit', selected[ClusterTypes.TENDBHA]);
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.instance_address && !modelValue.value.bk_host_id) {
        queryHost({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: [ClusterTypes.TENDBHA],
          db_type: DBTypes.MYSQL,
          instance_addresses: [modelValue.value.instance_address],
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
