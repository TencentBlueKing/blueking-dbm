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
    field="host.ip"
    fixed="left"
    :label="t('目标主机')"
    :loading="loading"
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
      v-model.trim="modelValue.ip"
      :placeholder="t('请输入IP')"
      @change="handleInputChange" />
  </EditableColumn>
  <EditableColumn
    field="host.related_instances"
    :label="t('关联集群实例')"
    :loading="loading"
    :min-width="220"
    readonly>
    <EditableBlock :placeholder="t('自动生成')">
      <div
        v-for="item in modelValue.related_instances"
        :key="item.instance_address">
        <p>
          {{ item.master_domain }}
        </p>
        <p style="color: #979ba5">--{{ item.instance_address }}</p>
      </div>
    </EditableBlock>
  </EditableColumn>
  <HostSelector
    v-model="selectedInstances"
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]"
    :data-source-map="dataSourceMap"
    :tab-name-map="{
      [ClusterTypes.SQLSERVER_HA]: t('SqlServer 主从'),
      [ClusterTypes.SQLSERVER_SINGLE]: t('SqlServer 单节点'),
    }"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import SqlserverHaModel from '@services/model/sqlserver/sqlserver-ha';
  import { checkInstance } from '@services/source/dbbase';
  import { getMachineList } from '@services/source/sqlserveHaCluster';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import HostSelector, { type HostModel, type HostSelectorValues } from '@components/host-selector/Index.vue';

  export type SelectorHost = HostModel<ClusterTypes.SQLSERVER_HA> | HostModel<ClusterTypes.SQLSERVER_SINGLE>;

  interface Props {
    selected: {
      cluster_type: ClusterTypes;
      ip: string;
    }[];
  }

  type Emits = (e: 'batch-edit', list: SelectorHost[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_cloud_id: number;
    bk_host_id: number;
    bk_idc_city_name: string;
    bk_sub_zone: string;
    cluster_type: ClusterTypes;
    ip: string;
    related_instances: ServiceReturnType<typeof checkInstance>;
    spec: SqlserverHaModel['masters'][0]['spec_config'];
  }>({
    required: true,
  });

  const { t } = useI18n();

  // 主从/单节点主机分别按角色过滤
  const dataSourceMap = {
    [ClusterTypes.SQLSERVER_HA]: (params: ServiceParameters<typeof getMachineList>) =>
      getMachineList({
        ...params,
        instance_role: 'backend_master',
      }),
    [ClusterTypes.SQLSERVER_SINGLE]: (params: ServiceParameters<typeof getMachineList>) =>
      getMachineList({
        ...params,
        instance_role: 'orphan',
      }),
  };

  const showSelector = ref(false);
  const selectedInstances = computed<HostSelectorValues<ClusterTypes.SQLSERVER_HA | ClusterTypes.SQLSERVER_SINGLE>>(
    () => ({
      [ClusterTypes.SQLSERVER_HA]: props.selected
        .filter((item) => item.cluster_type === ClusterTypes.SQLSERVER_HA)
        .map(
          (item) =>
            ({
              ip: item.ip,
            }) as SelectorHost,
        ),
      [ClusterTypes.SQLSERVER_SINGLE]: props.selected
        .filter((item) => item.cluster_type === ClusterTypes.SQLSERVER_SINGLE)
        .map(
          (item) =>
            ({
              ip: item.ip,
            }) as SelectorHost,
        ),
    }),
  );

  const rules = [
    {
      message: t('IP格式有误，请输入合法IP'),
      trigger: 'change',
      validator: (value: string) => !value || ipv4.test(value),
    },
    {
      message: t('目标主机重复'),
      trigger: 'change',
      validator: (value: string) => !value || props.selected.filter((item) => item.ip === value).length < 2,
    },
    {
      message: t('目标主机不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.bk_host_id),
    },
  ];

  const { loading, run: queryHost } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      const relatedInstances = data;
      const [currentHost] = data;
      if (currentHost) {
        modelValue.value = {
          bk_cloud_id: currentHost.bk_cloud_id,
          bk_host_id: currentHost.bk_host_id,
          bk_idc_city_name: currentHost.host_info?.bk_idc_city_name || '',
          bk_sub_zone: currentHost.host_info?.bk_sub_zone || '',
          cluster_type: currentHost.cluster_type,
          ip: currentHost.ip,
          related_instances: relatedInstances,
          spec: currentHost.spec_config,
        };
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = Object.assign({} as typeof modelValue.value, {
      bk_cloud_id: 0,
      bk_host_id: 0,
      bk_idc_city_name: '',
      bk_sub_zone: '',
      ip: value,
      related_instances: [],
      spec: {
        id: 0,
      },
    });
  };

  const handleSelectorChange = (
    selected: HostSelectorValues<ClusterTypes.SQLSERVER_HA | ClusterTypes.SQLSERVER_SINGLE>,
  ) => {
    emits('batch-edit', [
      ...(selected[ClusterTypes.SQLSERVER_HA] || []),
      ...(selected[ClusterTypes.SQLSERVER_SINGLE] || []),
    ]);
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.ip && !modelValue.value.bk_host_id) {
        queryHost({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: [ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE],
          db_type: DBTypes.SQLSERVER,
          instance_addresses: [modelValue.value.ip],
          instance_role: ['backend_master', 'orphan'],
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
