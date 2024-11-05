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
  <BkLoading :loading="isResourceSpecLoading">
    <BkComposeFormItem class="search-spec-id">
      <BkSelect
        v-model="currentCluster"
        :clearable="false"
        filterable
        :input-search="false"
        style="width: 150px"
        @change="handleCluserChange">
        <BkOption
          v-for="(item, index) in clusterList"
          :key="`${item}#${index}`"
          :label="item.label"
          :value="item.name" />
      </BkSelect>
      <BkSelect
        :key="currentCluster"
        v-model="currentMachine"
        :clearable="false"
        :disabled="!currentCluster"
        filterable
        :input-search="false"
        style="width: 150px">
        <BkOption
          v-for="item in clusterMachineList"
          :key="item.label"
          :label="item.label"
          :value="item.name" />
      </BkSelect>
      <BkSelect
        :key="currentMachine"
        :disabled="!currentMachine"
        filterable
        :input-search="false"
        :loading="isResourceSpecListLoading"
        :model-value="defaultValue || undefined"
        :placeholder="t('请选择匹配规格')"
        @change="handleChange">
        <BkOption
          v-for="item in resourceSpecList?.results"
          :key="item.spec_id"
          :label="item.spec_name"
          :value="item.spec_id" />
      </BkSelect>
    </BkComposeFormItem>
  </BkLoading>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getResourceSpec, getResourceSpecList } from '@services/source/dbresourceSpec';

  import { DBTypes } from '@common/const';

  interface Props {
    defaultValue?: number;
  }
  interface Emits {
    (e: 'change', value: Props['defaultValue']): void;
  }
  interface Expose {
    reset: () => void;
  }

  const emits = defineEmits<Emits>();

  defineOptions({
    inheritAttrs: false,
  });

  const defaultValue = defineModel<Props['defaultValue']>('defaultValue');

  const { t } = useI18n();

  const clusterList = [
    {
      moduleId: 'mysql',
      label: 'MySql',
      name: DBTypes.MYSQL,
      children: [
        {
          label: 'Proxy',
          name: 'proxy',
        },
        {
          label: t('后端存储'),
          name: 'backend',
        },
      ],
    },
    {
      moduleId: 'mysql',
      label: 'TenDBCluster',
      name: DBTypes.TENDBCLUSTER,
      children: [
        {
          label: t('接入层Master'),
          name: 'proxy',
        },
        {
          label: t('后端存储规格'),
          name: 'backend',
        },
      ],
    },
    {
      moduleId: 'redis',
      label: 'Redis',
      name: DBTypes.REDIS,
      children: [
        {
          label: 'Proxy',
          name: 'proxy',
        },
        {
          label: t('TendisCache后端存储'),
          name: 'TwemproxyRedisInstance',
        },
        {
          label: t('TendisSSD后端存储'),
          name: 'TwemproxyTendisSSDInstance',
        },
        {
          label: t('TendisPlus后端存储'),
          name: 'PredixyTendisplusCluster',
        },
        {
          label: 'RedisCluster',
          name: 'PredixyRedisCluster',
        },
        {
          label: t('Redis主从'),
          name: 'RedisInstance',
        },
      ],
    },
    {
      moduleId: 'bigdata',
      label: 'ES',
      name: DBTypes.ES,
      children: [
        {
          label: t('Master节点'),
          name: 'es_master',
        },
        {
          label: t('Client节点'),
          name: 'es_client',
        },
        {
          label: t('冷_热节点'),
          name: 'es_datanode',
        },
      ],
    },
    {
      moduleId: 'bigdata',
      label: 'HDFS',
      name: DBTypes.HDFS,
      children: [
        {
          label: t('DataNode节点'),
          name: 'hdfs_datanode',
        },
        {
          label: t('NameNode_Zookeeper_JournalNode节点'),
          name: 'hdfs_master',
        },
      ],
    },
    {
      moduleId: 'bigdata',
      label: 'Kafka',
      name: DBTypes.KAFKA,
      children: [
        {
          label: t('Zookeeper节点'),
          name: 'zookeeper',
        },
        {
          label: t('Broker节点'),
          name: 'broker',
        },
      ],
    },
    // {
    //   moduleId: 'bigdata',
    //   label: 'InfluxDB',
    //   name: ClusterTypes.INFLUXDB,
    //   children: [
    //     {
    //       label: t('后端存储机型'),
    //       name: 'influxdb',
    //     },
    //   ],
    // },
    {
      moduleId: 'bigdata',
      label: 'Pulsar',
      name: DBTypes.PULSAR,
      children: [
        {
          label: t('Bookkeeper节点'),
          name: 'pulsar_bookkeeper',
        },
        {
          label: t('Zookeeper节点'),
          name: 'pulsar_zookeeper',
        },
        {
          label: t('Broker节点'),
          name: 'pulsar_broker',
        },
      ],
    },
    {
      moduleId: 'bigdata',
      label: 'Riak',
      name: DBTypes.RIAK,
      children: [
        {
          label: t('后端存储'),
          name: 'riak',
        },
      ],
    },
    {
      moduleId: 'mongodb',
      label: 'MongoDB',
      name: DBTypes.MONGODB,
      children: [
        {
          label: 'ConfigSvr',
          name: 'mongo_config',
        },
        {
          label: 'Mongos',
          name: 'mongos',
        },
        {
          label: t('副本集/ShardSvr'),
          name: 'mongodb',
        },
      ],
    },
    {
      moduleId: 'sqlserver',
      label: 'SQLServer',
      name: DBTypes.SQLSERVER,
      children: [
        {
          label: t('后端存储'),
          name: 'sqlserver',
        },
      ],
    },
  ];

  // 临时修复 bk-select 无法重置的问题
  const rerenderKey = ref(0);

  const currentCluster = ref('');
  const currentMachine = ref('');
  const clusterMachineList = ref<Record<'label' | 'name', string>[]>([]);

  const { loading: isResourceSpecLoading, run: fetchResourceSpecDetail } = useRequest(getResourceSpec, {
    manual: true,
    onSuccess(data) {
      currentCluster.value = data.spec_cluster_type;

      const clusterData = _.find(clusterList, (item) => item.name === currentCluster.value);
      if (!clusterData) {
        return;
      }
      currentMachine.value = data.spec_machine_type;
      clusterMachineList.value = clusterData.children;
    },
  });
  const {
    loading: isResourceSpecListLoading,
    data: resourceSpecList,
    run: fetchResourceSpecList,
  } = useRequest(getResourceSpecList, {
    manual: true,
  });

  watch(
    defaultValue,
    () => {
      if (defaultValue.value === undefined) {
        currentCluster.value = '';
        currentMachine.value = '';
      } else if (!currentCluster.value && !currentMachine.value && defaultValue.value) {
        // 通过规格ID获取规格详情
        fetchResourceSpecDetail({
          spec_id: defaultValue.value,
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    currentMachine,
    () => {
      if (currentMachine.value) {
        fetchResourceSpecList({
          spec_cluster_type: currentCluster.value,
          spec_machine_type: currentMachine.value,
          limit: -1,
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleCluserChange = () => {
    const clusterData = _.find(clusterList, (item) => item.name === currentCluster.value);
    defaultValue.value = 0;
    currentMachine.value = '';
    if (!clusterData) {
      clusterMachineList.value = [];
      return;
    }
    currentMachine.value = clusterData.children[0].name;
    clusterMachineList.value = clusterData.children;
  };

  const handleChange = (value: Props['defaultValue']) => {
    defaultValue.value = value;
    emits('change', value);
  };

  defineExpose<Expose>({
    reset() {
      rerenderKey.value = Date.now();
      (currentCluster.value = ''), (currentMachine.value = '');

      clusterMachineList.value = [];
    },
  });
</script>
<style lang="less" scoped>
  .search-spec-id {
    display: flex;
    width: 100%;

    :deep(.bk-compose-form-item-tail) {
      flex: 1;
    }
  }
</style>
