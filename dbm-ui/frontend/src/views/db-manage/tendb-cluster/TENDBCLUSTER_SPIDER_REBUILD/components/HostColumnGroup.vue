<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <EditableColumn
    :append-rules="rules"
    field="originSpider.instance_address"
    fixed="left"
    :label="t('目标实例')"
    :loading="loading"
    :min-width="220"
    required>
    <template #headAppend>
      <span
        v-bk-tooltips="t('从已有实例中选择')"
        class="batch-host-select"
        @click="handleShowSelector">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <EditableInput
      v-model="modelValue.instance_address"
      :placeholder="t('请输入 IP:Port')"
      @change="handleChange" />
  </EditableColumn>
  <EditableColumn
    field="originSpider.role"
    :label="t('角色')"
    :loading="loading"
    :min-width="140"
    readonly
    :rowspan="roleRowspan">
    <EditableBlock :placeholder="t('自动生成')">
      <span v-if="modelValue.role">{{ roleLabelMap[modelValue.role] || modelValue.role }}</span>
    </EditableBlock>
  </EditableColumn>
  <EditableColumn
    field="originSpider.cluster_id"
    :label="t('所属集群')"
    :loading="loading"
    :min-width="220"
    readonly
    :rowspan="rowspan">
    <EditableBlock :placeholder="t('自动生成')">
      <span v-if="modelValue.master_domain">{{ modelValue.master_domain }}</span>
    </EditableBlock>
  </EditableColumn>
  <EditableColumn
    :label="t('状态')"
    :loading="loading"
    :min-width="120"
    readonly>
    <EditableBlock :placeholder="t('自动生成')">
      <DbStatus
        v-if="modelValue.status"
        :theme="statusTheme">
        {{ statusLabel }}
      </DbStatus>
    </EditableBlock>
  </EditableColumn>
  <InstanceSelector
    v-model="selectedInstances"
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.TENDBCLUSTER]"
    :data-source-map="dataSourceMap"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { computed, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbInstanceModel from '@services/model/tendbcluster/tendbcluster-instance';
  import { checkInstance } from '@services/source/dbbase';
  import { getTendbclusterInstanceList } from '@services/source/tendbcluster';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipPort } from '@common/regex';

  import DbStatus from '@components/db-status/index.vue';
  import InstanceSelector from '@components/instance-selector-new/Index.vue';

  export type SelectorHost = TendbInstanceModel;

  interface Props {
    handleRowMerge: () => void;
    roleRowspan: number;
    rowspan: number;
    selected: Array<typeof modelValue.value>;
  }

  type Emits = (e: 'batch-edit', list: TendbInstanceModel[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_cloud_id: number;
    bk_host_id: number;
    cluster_id: number;
    instance_address: string;
    ip: string;
    master_domain: string;
    port: number;
    role: string;
    status: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const dataSourceMap = {
    [ClusterTypes.TENDBCLUSTER]: (params: ServiceParameters<typeof getTendbclusterInstanceList>) =>
      getTendbclusterInstanceList({
        ...params,
        role: 'spider_master,spider_slave,spider_mnt',
      }),
  };

  const statusTheme = computed(() => {
    const s = modelValue.value.status;
    if (!s) return 'default';
    if (s === 'running' || s === 'available') return 'success';
    if (s === 'unavailable') return 'danger';
    if (s === 'upgrading') return 'primary';
    return 'warning'; // restoring
  });

  const statusLabel = computed(() => {
    const s = modelValue.value.status;
    if (!s) return '-';
    const labelMap: Record<string, string> = {
      available: t('可用'),
      restoring: t('重建中'),
      running: t('运行中'),
      unavailable: t('不可用'),
      upgrading: t('升级中'),
    };
    return labelMap[s] || s;
  });

  const roleLabelMap: Record<string, string> = {
    spider_master: 'Spider Master',
    spider_mnt: 'Spider mnt',
    spider_slave: 'Spider Slave',
  };

  const showSelector = ref(false);
  const selectedInstances = computed(() => ({
    [ClusterTypes.TENDBCLUSTER]: props.selected.map((item) => ({
      instance_address: item.instance_address,
    })) as TendbInstanceModel[],
  }));

  const rules = [
    {
      message: t('实例格式有误，请输入 IP:Port'),
      trigger: 'blur',
      validator: (value: string) => !value || ipPort.test(value),
    },
    {
      message: t('目标实例重复'),
      trigger: 'blur',
      validator: (value: string) =>
        !value || props.selected.filter((item) => item.instance_address === value).length < 2,
    },
    {
      message: t('目标实例不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.bk_host_id),
    },
    {
      message: t('该实例为非接入层实例，请选择 Spider 实例'),
      trigger: 'blur',
      validator: (value: string) =>
        !value ||
        modelValue.value.role === 'spider_master' ||
        modelValue.value.role === 'spider_slave' ||
        modelValue.value.role === 'spider_mnt',
    },
  ];

  const { loading, run: queryInstance } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      const [item] = data;
      if (item) {
        modelValue.value = {
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          cluster_id: item.cluster_id,
          instance_address: item.instance_address,
          ip: item.ip,
          master_domain: item.master_domain,
          port: item.port,
          role: item.role,
          status: (item as unknown as { status?: string }).status || '',
        };
        setTimeout(() => {
          props.handleRowMerge();
        });
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleSelectorChange = (selected: { [ClusterTypes.TENDBCLUSTER]: TendbInstanceModel[] }) => {
    emits(
      'batch-edit',
      Object.values(selected).flatMap((item) => item),
    );
  };

  const handleChange = (value: string) => {
    modelValue.value = {
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      instance_address: value,
      ip: '',
      master_domain: '',
      port: 0,
      role: '',
      status: '',
    };
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.instance_address && !modelValue.value.bk_host_id) {
        queryInstance({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: [ClusterTypes.TENDBCLUSTER],
          db_type: DBTypes.TENDBCLUSTER,
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
