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
    field="master.ip"
    fixed="left"
    :label="t('故障主库主机')"
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
      v-model="modelValue.ip"
      :placeholder="t('请输入IP')"
      @change="handleInputChange" />
  </EditableColumn>
  <InstanceSelector
    v-model:is-show="showSelector"
    :cluster-types="['TendbhaHost']"
    :selected="selectedInstances"
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkInstance } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  export type SelectorHost = IValue;

  interface Props {
    selected: {
      ip: string;
    }[];
  }

  type Emits = (e: 'batch-edit', list: IValue[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
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
    TendbhaHost: [
      {
        id: 'TendbhaHost',
        name: t('故障主库主机'),
        tableConfig: {
          firsrColumn: {
            field: 'ip',
            label: t('Master 主机'),
            role: 'backend_master',
          },
        },
      },
      {
        id: 'manualInput',
        name: t('手动输入'),
        tableConfig: {
          firsrColumn: {
            field: 'ip',
            label: t('Master 主机'),
            role: 'backend_master',
          },
        },
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  const showSelector = ref(false);
  const selectedInstances = computed<InstanceSelectorValues<IValue>>(() => ({
    TendbhaHost: props.selected.map(
      (item) =>
        ({
          ip: item.ip,
        }) as IValue,
    ),
  }));

  const rules = [
    {
      message: t('IP 格式不符合IPv4标准'),
      trigger: 'blur',
      validator: (value: string) => !value || ipv4.test(value),
    },
    {
      message: t('目标主机不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.bk_host_id),
    },
    {
      message: t('非 Master IP'),
      trigger: 'blur',
      validator: (value: string) => !value || modelValue.value.role === 'backend_master',
    },
  ];

  const { loading, run: queryHost } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      const [currentHost] = data;
      if (currentHost) {
        modelValue.value = {
          bk_cloud_id: currentHost.bk_cloud_id,
          bk_host_id: currentHost.bk_host_id,
          ip: currentHost.ip,
          related_clusters: currentHost.related_clusters.map((item) => ({
            id: item.id,
            master_domain: item.master_domain,
          })),
          role: currentHost.role,
        };
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = {
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: value,
      related_clusters: [],
      role: '',
    };
  };

  const handleSelectorChange = (selected: InstanceSelectorValues<IValue>) => {
    emits('batch-edit', selected.TendbhaHost);
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.ip && !modelValue.value.bk_host_id) {
        queryHost({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: [ClusterTypes.TENDBHA],
          db_type: DBTypes.MYSQL,
          instance_addresses: [modelValue.value.ip],
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

  .table-cell {
    padding: 0 8px;
  }
</style>
