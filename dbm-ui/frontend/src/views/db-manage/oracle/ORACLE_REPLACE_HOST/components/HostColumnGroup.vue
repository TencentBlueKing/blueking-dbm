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
    field="host.ip"
    fixed="left"
    :label="t('主机')"
    :loading="loading"
    :min-width="190"
    required>
    <template #headAppend>
      <span
        v-bk-tooltips="t('从单节点主机与从库所在主机中选择')"
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
  <EditableColumn
    field="host.role"
    :label="t('角色')"
    :loading="loading"
    :min-width="110"
    readonly>
    <EditableBlock :placeholder="t('自动生成')">
      <span v-if="modelValue.role">{{ modelValue.role }}</span>
    </EditableBlock>
  </EditableColumn>
  <EditableColumn
    field="host.status"
    :label="t('状态')"
    :loading="loading"
    :min-width="100"
    readonly>
    <EditableBlock :placeholder="t('自动生成')">
      <ClusterInstanceStatus
        v-if="modelValue.status"
        :data="modelValue.status" />
    </EditableBlock>
  </EditableColumn>
  <EditableColumn
    field="host.master_domain"
    :label="t('所属集群')"
    :loading="loading"
    :min-width="220"
    readonly>
    <EditableBlock :placeholder="t('自动生成')">
      <span v-if="modelValue.master_domain">{{ modelValue.master_domain }}</span>
    </EditableBlock>
  </EditableColumn>
  <EditableColumn
    field="host.replication_source"
    :label="t('复制源')"
    :loading="loading"
    :min-width="200"
    readonly>
    <EditableBlock :placeholder="t('自动生成')">
      <template v-if="modelValue.replication_source.address">
        <span class="replication-source">
          <span class="replication-source__addr">{{ modelValue.replication_source.address }}</span>
          <span class="replication-source__role">{{ modelValue.replication_source.role }}</span>
        </span>
      </template>
    </EditableBlock>
  </EditableColumn>
  <EditableColumn
    field="host.cluster_type_name"
    :label="t('集群类型')"
    :loading="loading"
    :min-width="110"
    readonly>
    <EditableBlock :placeholder="t('自动生成')">
      <span v-if="modelValue.cluster_type_name">{{ modelValue.cluster_type_name }}</span>
    </EditableBlock>
  </EditableColumn>
  <HostSelector
    v-model="selectedHosts"
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.ORACLE_PRIMARY_STANDBY, ClusterTypes.ORACLE_SINGLE_NONE]"
    :data-source-map="dataSourceMap"
    single
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkInstance } from '@services/source/dbbase';
  import { getOracleHaInstanceList, getOracleHaMachineList } from '@services/source/oracleHaCluster';
  import { getOracleSingleMachineList } from '@services/source/oracleSingleCluster';

  import { ClusterInstStatusKeys, clusterTypeInfos, ClusterTypes, DBTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';
  import HostSelector from '@components/host-selector/Index.vue';
  import type { HostSelectorValues } from '@components/host-selector/types';

  import type { ReplaceHost, SelectorMachine } from '../types';
  import { computeReplicationSource, createReplaceHost } from '../types';

  interface Props {
    selected: {
      cluster_type?: ClusterTypes | '';
      instance_address?: string;
      ip: string;
    }[];
  }

  type Emits = (e: 'batch-edit', list: SelectorMachine[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<ReplaceHost>({
    required: true,
  });

  const { t } = useI18n();

  // 主从 tab 只列从库主机（instance_role=standby），单节点 tab 列单点主机
  const dataSourceMap = {
    [ClusterTypes.ORACLE_PRIMARY_STANDBY]: (params: ServiceParameters<typeof getOracleHaMachineList>) =>
      getOracleHaMachineList({
        ...params,
        instance_role: 'standby',
      }),
    [ClusterTypes.ORACLE_SINGLE_NONE]: (params: ServiceParameters<typeof getOracleSingleMachineList>) =>
      getOracleSingleMachineList(params),
  };

  const showSelector = ref(false);
  const selectedHosts = computed<
    HostSelectorValues<ClusterTypes.ORACLE_PRIMARY_STANDBY | ClusterTypes.ORACLE_SINGLE_NONE>
  >(() => {
    // 按 cluster_type 分配到对应 tab，避免同一 IP 在两个 tab 中重复出现
    const haList: SelectorMachine[] = [];
    const singleList: SelectorMachine[] = [];
    props.selected.forEach((item) => {
      const host = { ip: item.ip } as SelectorMachine;
      if (item.cluster_type === ClusterTypes.ORACLE_SINGLE_NONE) {
        singleList.push(host);
      } else {
        haList.push(host);
      }
    });
    return {
      [ClusterTypes.ORACLE_PRIMARY_STANDBY]: haList,
      [ClusterTypes.ORACLE_SINGLE_NONE]: singleList,
    };
  });

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
      message: t('主机不包含任何从库实例'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.bk_host_id),
    },
  ];

  // 手输主机校验（Oracle 单机单实例，实例即主机；返回 InstanceInfos，无 cluster_type_name/version，需派生）
  // 异常从库的复制源反查由 watch + queryMasterForReplicationSource 统一处理，此处不重复
  const { loading, run: queryHost } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      const [currentHost] = data;
      // 仅单点实例与从库实例可替换，主库/空主机/非 Oracle 主机报「主机不包含任何从库实例」
      if (
        currentHost &&
        (currentHost.cluster_type === ClusterTypes.ORACLE_SINGLE_NONE || currentHost.role === 'standby')
      ) {
        // 关联集群版本（按 cluster_id 匹配）
        const majorVersion = currentHost.related_clusters?.find(
          (item) => item.id === currentHost.cluster_id,
        )?.major_version;

        modelValue.value = createReplaceHost({
          bk_cloud_id: currentHost.bk_cloud_id,
          bk_host_id: currentHost.bk_host_id,
          cluster_id: currentHost.cluster_id,
          cluster_type: currentHost.cluster_type,
          cluster_type_name: clusterTypeInfos[currentHost.cluster_type]?.name || '',
          instance_address: currentHost.instance_address,
          ip: currentHost.ip,
          master_domain: currentHost.master_domain,
          port: currentHost.port,
          replication_source: computeReplicationSource(currentHost),
          role: currentHost.role,
          specId: currentHost.spec_config?.id || 0,
          status: currentHost.status,
          version: (majorVersion || modelValue.value.version || '').replace(/^Oracle-/, ''),
        });
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    // 手输 IP：重置反查要素，触发 watch 校验主机候选资格
    modelValue.value = createReplaceHost({
      ip: value,
    });
  };

  const handleSelectorChange = (
    selected: HostSelectorValues<ClusterTypes.ORACLE_PRIMARY_STANDBY | ClusterTypes.ORACLE_SINGLE_NONE>,
  ) => {
    emits(
      'batch-edit',
      Object.values(selected).flatMap((item) => item),
    );
  };

  // §2.4 选择器路径补充：异常从库复制源地址为空（role=primary），需反查主库实例填充
  const { run: queryMasterForReplicationSource } = useRequest(getOracleHaInstanceList, {
    manual: true,
    onSuccess: (data) => {
      const [masterInstance] = data.results;
      if (masterInstance) {
        modelValue.value = {
          ...modelValue.value,
          replication_source: {
            address: masterInstance.instance_address,
            bk_cloud_id: masterInstance.bk_cloud_id,
            bk_host_id: masterInstance.bk_host_id,
            ip: masterInstance.ip,
            port: masterInstance.port,
            role: 'primary',
          },
        };
      }
    },
  });

  watch(
    modelValue,
    () => {
      if (modelValue.value.ip && !modelValue.value.bk_host_id) {
        queryHost({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: [ClusterTypes.ORACLE_SINGLE_NONE, ClusterTypes.ORACLE_PRIMARY_STANDBY],
          db_type: DBTypes.ORACLE,
          instance_addresses: [modelValue.value.ip],
        });
      }
      // 选择器路径：异常从库复制源地址缺失，反查主库补充
      if (
        modelValue.value.bk_host_id &&
        modelValue.value.cluster_type === ClusterTypes.ORACLE_PRIMARY_STANDBY &&
        modelValue.value.role === 'standby' &&
        modelValue.value.status !== ClusterInstStatusKeys.RUNNING &&
        !modelValue.value.replication_source.address
      ) {
        queryMasterForReplicationSource({
          cluster_id: modelValue.value.cluster_id,
          role: 'primary',
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

  .replication-source {
    display: inline-flex;
    column-gap: 8px;
    align-items: baseline;

    &__addr {
      font-family: 'JetBrains Mono', Consolas, monospace;
      font-size: 12px;
      color: #313238;
    }

    &__role {
      font-size: 12px;
      color: #979ba5;
    }
  }
</style>
