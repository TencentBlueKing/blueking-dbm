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
    field="upstreamInstance.instance_address"
    fixed="left"
    :label="t('上游实例')"
    :min-width="220"
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
      :placeholder="t('请输入 IP:Port')"
      @change="handleInputChange" />
  </EditableColumn>
  <InstanceSelector
    v-model="selectedInstances"
    v-model:is-show="showSelector"
    :cluster-types="clusterTypes"
    :data-source-map="dataSourceMap"
    single
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import OracleHaInstanceModel from '@services/model/oracle/oracle-ha-instance';
  import OracleSingleInstanceModel from '@services/model/oracle/oracle-single-instance';
  import { checkInstance } from '@services/source/dbbase';
  import { getOracleHaInstanceList } from '@services/source/oracleHaCluster';
  import { getOracleSingleInstanceList } from '@services/source/oracleSingleCluster';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipPort } from '@common/regex';

  import InstanceSelector from '@components/instance-selector-new/Index.vue';

  import type { UpstreamInstance, UpstreamMode } from '../types';
  import { createUpstreamInstance } from '../types';

  type InstanceModel = OracleHaInstanceModel | OracleSingleInstanceModel;

  interface Props {
    mode: UpstreamMode;
    selected: UpstreamInstance[];
  }

  type Emits = (e: 'batch-edit', list: InstanceModel[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<UpstreamInstance>({
    required: true,
  });

  const { t } = useI18n();

  // 根据 mode 决定选择器与实例校验的候选集群类型，标注精确联合类型供 InstanceSelector 泛型推断
  type OracleClusterType = typeof ClusterTypes.ORACLE_PRIMARY_STANDBY | typeof ClusterTypes.ORACLE_SINGLE_NONE;
  const clusterTypes = computed<OracleClusterType[]>(() =>
    props.mode === 'single' ? [ClusterTypes.ORACLE_SINGLE_NONE] : [ClusterTypes.ORACLE_PRIMARY_STANDBY],
  );

  // 主从集群按 mode 过滤角色：master → primary，slave → standby
  const dataSourceMap = {
    [ClusterTypes.ORACLE_PRIMARY_STANDBY]: (params: ServiceParameters<typeof getOracleHaInstanceList>) =>
      getOracleHaInstanceList({
        ...params,
        role: props.mode === 'master' ? 'primary' : 'standby',
      }),
    [ClusterTypes.ORACLE_SINGLE_NONE]: (params: ServiceParameters<typeof getOracleSingleInstanceList>) =>
      getOracleSingleInstanceList(params),
  };

  const showSelector = ref(false);
  const selectedInstances = computed(() => {
    const list = props.selected.map(
      (item) =>
        ({
          instance_address: `${item.ip}:${item.port}`,
        }) as InstanceModel,
    );
    return {
      [ClusterTypes.ORACLE_PRIMARY_STANDBY]: list,
      [ClusterTypes.ORACLE_SINGLE_NONE]: list,
    };
  });

  const rules = [
    {
      message: t('实例格式有误，请输入 IP:Port'),
      trigger: 'change',
      validator: (value: string) => !value || ipPort.test(value),
    },
    {
      message: t('上游实例重复'),
      trigger: 'change',
      validator: (value: string) =>
        !value || props.selected.filter((item) => `${item.ip}:${item.port}` === value).length < 2,
    },
    {
      message: t('上游实例不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.bk_host_id),
    },
  ];

  // 手输实例校验：接口实际返回 Oracle 实例模型（含 version），InstanceInfos 类型未覆盖，此处断言取值
  const { run: queryHost } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      const [currentHost] = data as unknown as (OracleHaInstanceModel | OracleSingleInstanceModel)[];
      if (currentHost) {
        modelValue.value = createUpstreamInstance({
          bk_cloud_id: currentHost.bk_cloud_id,
          bk_host_id: currentHost.bk_host_id,
          cluster_id: currentHost.cluster_id,
          instance_address: currentHost.instance_address,
          ip: currentHost.ip,
          master_domain: currentHost.master_domain,
          port: currentHost.port,
          role: currentHost.role,
          spec_config: { id: currentHost.spec_config?.id || 0 },
          version: currentHost.version || '',
        });
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    // 手输地址：重置主机要素，触发 watch 校验实例存在性
    modelValue.value = createUpstreamInstance({
      instance_address: value,
    });
  };

  const handleSelectorChange = (selected: {
    [ClusterTypes.ORACLE_PRIMARY_STANDBY]: OracleHaInstanceModel[];
    [ClusterTypes.ORACLE_SINGLE_NONE]: OracleSingleInstanceModel[];
  }) => {
    emits(
      'batch-edit',
      Object.values(selected).flatMap((item) => item),
    );
  };
  watch(
    modelValue,
    () => {
      if (modelValue.value.instance_address && !modelValue.value.bk_host_id) {
        queryHost({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: clusterTypes.value,
          db_type: DBTypes.ORACLE,
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
