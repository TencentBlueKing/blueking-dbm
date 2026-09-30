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
    field="master.ip"
    fixed="left"
    :label="t('主库主机')"
    :loading="loading"
    :min-width="190"
    required>
    <template #headAppend>
      <span
        v-bk-tooltips="t('从主从集群的主库主机中选择')"
        class="batch-host-select"
        @click="handleShowSelector">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <EditableInput
      v-model.trim="modelValue.ip"
      :placeholder="t('请输入主机 IP')"
      @change="handleInputChange" />
  </EditableColumn>
  <HostSelector
    v-model="selectedHosts"
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.ORACLE_PRIMARY_STANDBY]"
    :data-source-map="dataSourceMap"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkInstance } from '@services/source/dbbase';
  import { getOracleHaMachineList } from '@services/source/oracleHaCluster';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import HostSelector from '@components/host-selector/Index.vue';
  import type { HostSelectorValues } from '@components/host-selector/types';

  import type { FailOverMaster, SelectorMachine } from '../types';
  import { createFailOverMaster } from '../types';

  interface Props {
    selected: {
      ip: string;
    }[];
  }

  type Emits = (e: 'batch-edit', list: SelectorMachine[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<FailOverMaster>({
    required: true,
  });

  const { t } = useI18n();

  // 主从 tab 只列主库主机（instance_role=primary）
  const dataSourceMap = {
    [ClusterTypes.ORACLE_PRIMARY_STANDBY]: (params: ServiceParameters<typeof getOracleHaMachineList>) =>
      getOracleHaMachineList({
        ...params,
        instance_role: 'primary',
      }),
  };

  const showSelector = ref(false);
  const selectedHosts = computed<HostSelectorValues<ClusterTypes.ORACLE_PRIMARY_STANDBY>>(() => ({
    [ClusterTypes.ORACLE_PRIMARY_STANDBY]: props.selected.map((item) => ({ ip: item.ip }) as SelectorMachine),
  }));

  const rules = [
    {
      message: t('IP格式有误，请输入合法IP'),
      trigger: 'change',
      validator: (value: string) => !value || ipv4.test(value),
    },
    {
      message: t('主机重复'),
      trigger: 'change',
      validator: (value: string) => !value || props.selected.filter((item) => item.ip === value).length < 2,
    },
    {
      message: t('主机不包含任何主库实例'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.bk_host_id),
    },
  ];

  // 手输主机校验（Oracle 单机单实例，实例即主机）：仅主从集群主库实例可作为故障主库
  const { loading, run: queryHost } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      const [currentHost] = data;
      if (
        currentHost &&
        currentHost.cluster_type === ClusterTypes.ORACLE_PRIMARY_STANDBY &&
        currentHost.role === 'primary'
      ) {
        modelValue.value = createFailOverMaster({
          bk_cloud_id: currentHost.bk_cloud_id,
          bk_host_id: currentHost.bk_host_id,
          cluster_id: currentHost.cluster_id,
          ip: currentHost.ip,
          master_domain: currentHost.master_domain,
          role: currentHost.role,
        });
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    // 手输 IP：重置反查要素，触发 watch 校验主机候选资格
    modelValue.value = createFailOverMaster({
      ip: value,
    });
  };

  const handleSelectorChange = (selected: HostSelectorValues<ClusterTypes.ORACLE_PRIMARY_STANDBY>) => {
    emits('batch-edit', selected[ClusterTypes.ORACLE_PRIMARY_STANDBY]);
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.ip && !modelValue.value.bk_host_id) {
        queryHost({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: [ClusterTypes.ORACLE_PRIMARY_STANDBY],
          db_type: DBTypes.ORACLE,
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
</style>
