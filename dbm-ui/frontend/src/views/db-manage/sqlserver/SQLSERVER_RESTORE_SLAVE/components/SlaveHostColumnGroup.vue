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
    field="slave.ip"
    fixed="left"
    :label="t('目标从库主机')"
    :loading="loading"
    :min-width="240"
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
  <EditableColumn
    :label="t('同机关联集群')"
    :loading="loading"
    :min-width="300"
    readonly>
    <EditableBlock v-if="modelValue.related_clusters.length">
      <p
        v-for="item in modelValue.related_clusters"
        :key="item.id">
        {{ item.master_domain }}
      </p>
    </EditableBlock>
    <EditableBlock
      v-else
      :placeholder="t('自动生成')" />
  </EditableColumn>
  <HostSelector
    v-model="selectedInstances"
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.SQLSERVER_HA]"
    :data-source-map="dataSourceMap"
    :tab-name-map="{ [ClusterTypes.SQLSERVER_HA]: t('Slave 主机') }"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  // import { getLevelConfig } from '@services/source/configs';
  import { getGlobalMachine } from '@services/source/dbbase';
  import { getMachineList } from '@services/source/sqlserveHaCluster';

  import { ClusterTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import HostSelector, { type HostModel, type HostSelectorValues } from '@components/host-selector/Index.vue';

  interface Props {
    selected: {
      ip: string;
    }[];
  }

  type Emits = (e: 'batch-edit', list: HostModel<ClusterTypes.SQLSERVER_HA>[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_cloud_id: number;
    bk_host_id?: number;
    // db_module_id: number;
    ip: string;
    related_clusters: {
      id: number;
      master_domain: string;
      region: string;
    }[];
    spec_config: {
      id: number;
    };
    // system_version: string;
  }>({
    default: () => ({
      bk_cloud_id: 0,
      bk_host_id: undefined,
      // db_module_id: 0,
      ip: '',
      related_clusters: [],
      // system_version: '',
    }),
  });

  const { t } = useI18n();

  // 从库主机：默认角色过滤改为 backend_slave
  const dataSourceMap = {
    [ClusterTypes.SQLSERVER_HA]: (params: ServiceParameters<typeof getMachineList>) =>
      getMachineList({
        ...params,
        instance_role: 'backend_slave',
      }),
  };

  const showSelector = ref(false);
  const selectedInstances = computed<HostSelectorValues<ClusterTypes.SQLSERVER_HA>>(() => ({
    [ClusterTypes.SQLSERVER_HA]: props.selected.map(
      (item) =>
        ({
          ip: item.ip,
        }) as HostModel<ClusterTypes.SQLSERVER_HA>,
    ),
  }));

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

  const { loading, run: queryHost } = useRequest(getGlobalMachine, {
    manual: true,
    onSuccess: (data) => {
      if (data.results.length) {
        const [currentHost] = data.results;
        modelValue.value = {
          bk_cloud_id: currentHost.bk_cloud_id,
          bk_host_id: currentHost.bk_host_id,
          // db_module_id: currentHost.db_module_id,
          ip: currentHost.ip,
          related_clusters: currentHost.related_clusters.map((item) => ({
            id: item.id,
            master_domain: item.immute_domain,
            region: item.region,
          })),
          spec_config: {
            id: currentHost.spec_config.id,
          },
          // system_version: '',
        };
      }
    },
  });

  // const { run: getOsTypes } = useRequest(getLevelConfig, {
  //   manual: true,
  //   onSuccess: (data) => {
  //     modelValue.value.system_version =
  //       data.conf_items.find((item) => item.conf_name === 'system_version')?.conf_value || '';
  //   },
  // });

  watch(
    modelValue,
    () => {
      if (modelValue.value.ip && !modelValue.value.bk_host_id) {
        queryHost({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: ClusterTypes.SQLSERVER_HA,
          ip: modelValue.value.ip,
        });
      }
      // if (modelValue.value.db_module_id) {
      //   getOsTypes({
      //     bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      //     conf_type: 'deploy',
      //     level_name: 'module',
      //     level_value: modelValue.value.db_module_id,
      //     meta_cluster_type: SqlserverHaHost,
      //     version: 'deploy_info',
      //   });
      // }
    },
    {
      immediate: true,
    },
  );

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = {
      bk_cloud_id: 0,
      bk_host_id: undefined,
      // db_module_id: 0,
      ip: value,
      related_clusters: [],
      spec_config: {
        id: 0,
      },
      // system_version: '',
    };
    // if (value) {
    //   queryHost({
    //     bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    //     instance_addresses: [value],
    //   });
    // }
  };

  const handleSelectorChange = (selected: HostSelectorValues<ClusterTypes.SQLSERVER_HA>) => {
    emits('batch-edit', selected[ClusterTypes.SQLSERVER_HA]);
  };
</script>
<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
