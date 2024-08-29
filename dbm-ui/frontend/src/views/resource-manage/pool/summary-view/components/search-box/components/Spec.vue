<template>
  <BkComposeFormItem class="search-box-select-spec">
    <BkSelect
      v-model="currentCluster"
      style="width: 150px"
      @change="handleChangeCluster">
      <BkOption
        v-for="(item, index) in currentClusterList"
        :key="`${item}#${index}`"
        :label="item.label"
        :value="item.name" />
    </BkSelect>
    <BkSelect
      :key="currentCluster"
      v-model="currentMachine"
      :disabled="!currentCluster"
      style="width: 150px"
      @change="handleChangeMachine">
      <BkOption
        v-for="item in clusterMachineList"
        :key="item.label"
        :label="item.label"
        :value="item.name" />
    </BkSelect>
    <BkSelect
      :key="currentMachine"
      v-model:model-value="currentSpecIdList"
      collapse-tags
      :disabled="!currentMachine"
      :loading="isResourceSpecListLoading"
      multiple
      multiple-mode="tag"
      show-select-all
      @change="handleChange">
      <BkOption
        v-for="item in resourceSpecList?.results"
        :key="item.spec_id"
        :label="item.spec_name"
        :value="item.spec_id" />
    </BkSelect>
  </BkComposeFormItem>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { ClusterTypes, DBTypes, MachineTypes } from '@common/const';

  import { getResourceSpecList } from '@/services/source/dbresourceSpec';

  interface Props {
    dbType: DBTypes;
  }

  interface Emits {
    (e: 'change'): void;
  }

  interface Exposes {
    getValue: () => {
      spec_param: {
        db_type: DBTypes;
        machine_type: MachineTypes;
        cluster_type: ClusterTypes;
        spec_id_list: number[];
      };
    };
    reset: () => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    dbType: DBTypes.MYSQL,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const clusterList = [
    {
      label: t('MySQL单节点'),
      name: ClusterTypes.TENDBSINGLE,
      dbType: DBTypes.MYSQL,
      children: [
        {
          label: t('后端存储机型'),
          name: MachineTypes.SINGLE,
        },
      ],
    },
    {
      label: t('MySQL主从'),
      name: ClusterTypes.TENDBHA,
      dbType: DBTypes.MYSQL,
      children: [
        {
          label: t('后端存储机型'),
          name: MachineTypes.BACKEND,
        },
        {
          label: t('Proxy机型'),
          name: MachineTypes.PROXY,
        },
      ],
    },
    {
      label: 'TenDBCluster',
      name: ClusterTypes.TENDBCLUSTER,
      dbType: DBTypes.TENDBCLUSTER,
      children: [
        {
          label: t('接入层Master'),
          name: MachineTypes.SPIDER,
        },
        {
          label: t('后端存储规格'),
          name: MachineTypes.REMOTE,
        },
      ],
    },
    {
      label: 'TendisCache',
      name: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
      dbType: DBTypes.REDIS,
      children: [
        {
          label: t('后端存储机型'),
          name: MachineTypes.TENDISCACHE,
        },
        {
          label: t('Proxy机型'),
          name: MachineTypes.TWEMPROXY,
        },
      ],
    },
    {
      label: 'TendisSSD',
      name: ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
      dbType: DBTypes.REDIS,
      children: [
        {
          label: t('后端存储机型'),
          name: MachineTypes.TENDISSSD,
        },
        {
          label: t('Proxy机型'),
          name: MachineTypes.TWEMPROXY,
        },
      ],
    },
    {
      label: 'Tendisplus',
      name: ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
      dbType: DBTypes.REDIS,
      children: [
        {
          label: t('后端存储机型'),
          name: MachineTypes.TENDISPLUS,
        },
        {
          label: t('Proxy机型'),
          name: MachineTypes.PREDIXY,
        },
      ],
    },
    {
      label: 'RedisCluster',
      name: ClusterTypes.PREDIXY_REDIS_CLUSTER,
      dbType: DBTypes.REDIS,
      children: [
        {
          label: t('后端存储机型'),
          name: MachineTypes.TENDISCACHE,
        },
        {
          label: t('Proxy机型'),
          name: MachineTypes.PREDIXY,
        },
      ],
    },
    {
      label: t('Redis主从'),
      name: ClusterTypes.REDIS_INSTANCE,
      dbType: DBTypes.REDIS,
      children: [
        {
          label: t('后端存储机型'),
          name: MachineTypes.TENDISCACHE,
        },
      ],
    },
    {
      label: 'ES',
      name: ClusterTypes.ES,
      dbType: DBTypes.ES,
      children: [
        {
          label: t('Master节点规格'),
          name: MachineTypes.ES_MASTER,
        },
        {
          label: t('Client节点规格'),
          name: MachineTypes.ES_CLIENT,
        },
        {
          label: t('冷_热节点规格'),
          name: MachineTypes.ES_DATANODE,
        },
      ],
    },
    {
      label: 'HDFS',
      name: ClusterTypes.HDFS,
      dbType: DBTypes.HDFS,
      children: [
        {
          label: t('DataNode节点规格'),
          name: MachineTypes.HDFS_DATANODE,
        },
        {
          label: t('NameNode_Zookeeper_JournalNode节点规格'),
          name: MachineTypes.HDFS_MASTER,
        },
      ],
    },
    {
      label: 'Kafka',
      name: ClusterTypes.KAFKA,
      dbType: DBTypes.KAFKA,
      children: [
        {
          label: t('Zookeeper节点规格'),
          name: MachineTypes.ZOOKEEPER,
        },
        {
          label: t('Broker节点规格'),
          name: MachineTypes.BROKER,
        },
      ],
    },
    {
      label: 'InfluxDB',
      name: ClusterTypes.INFLUXDB,
      dbType: DBTypes.INFLUXDB,
      children: [
        {
          label: t('后端存储机型'),
          name: MachineTypes.INFLUXDB,
        },
      ],
    },
    {
      label: 'Pulsar',
      name: ClusterTypes.PULSAR,
      dbType: DBTypes.PULSAR,
      children: [
        {
          label: t('Bookkeeper节点规格'),
          name: MachineTypes.PULSAR_BOOKKEEPER,
        },
        {
          label: t('Zookeeper节点规格'),
          name: MachineTypes.PULSAR_ZOOKEEPER,
        },
        {
          label: t('Broker节点规格'),
          name: MachineTypes.PULSAR_BROKER,
        },
      ],
    },
  ];

  const currentCluster = ref('');
  const currentMachine = ref('');
  const currentSpecIdList = ref<number[]>([]);
  const clusterMachineList = ref<Record<'label' | 'name', string>[]>([]);

  const currentClusterList = computed(() => clusterList.filter((item) => item.dbType === props.dbType));

  const {
    loading: isResourceSpecListLoading,
    data: resourceSpecList,
    run: fetchResourceSpecList,
  } = useRequest(getResourceSpecList, {
    manual: true,
  });

  const reset = () => {
    currentCluster.value = '';
    currentMachine.value = '';
    currentSpecIdList.value = [];
  };

  watch(
    () => props.dbType,
    () => {
      reset();
    },
  );

  const handleChangeCluster = (value: ClusterTypes) => {
    const clusterData = _.find(clusterList, (item) => item.name === value);
    if (!clusterData) {
      clusterMachineList.value = [];
      return;
    }
    clusterMachineList.value = clusterData.children;
    emits('change');
  };

  const handleChangeMachine = (value: MachineTypes) => {
    fetchResourceSpecList({
      spec_cluster_type: currentCluster.value,
      spec_machine_type: value,
      limit: -1,
    });
    emits('change');
  };

  const handleChange = () => {
    emits('change');
  };

  defineExpose<Exposes>({
    getValue: () => ({
      spec_param: {
        db_type: props.dbType as DBTypes,
        machine_type: currentMachine.value as MachineTypes,
        cluster_type: currentCluster.value as ClusterTypes,
        spec_id_list: currentSpecIdList.value as number[],
      },
    }),
    reset,
  });
</script>

<style lang="less" scoped>
  .search-box-select-spec {
    display: flex;
    width: 100%;

    :deep(.bk-compose-form-item-tail) {
      flex: 1;
    }
  }
</style>
