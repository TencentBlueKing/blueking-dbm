<template>
  <div class="target-form-item">
    <div class="target-prefix">{{ t('集群') }}</div>
    <BkSelect
      v-model="modelValue"
      class="target-select"
      :class="{
        'is-error': Boolean(errorMessage),
      }"
      :clearable="false"
      collapse-tags
      filterable
      :input-search="false"
      multiple
      multiple-mode="tag"
      @change="handleChange">
      <BkOption
        v-for="item in clusterList"
        :key="item.id"
        :label="item.immute_domain"
        :value="item.id" />
    </BkSelect>
    <div
      v-if="errorMessage"
      class="error-icon">
      <DbIcon
        v-bk-tooltips="errorMessage"
        type="exclamation-fill" />
    </div>
    <div class="action-box">
      <DbIcon
        class="action-btn"
        type="minus-fill"
        @click="handleRemove" />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { queryAllTypeCluster } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';

  import useValidtor from '@components/render-table/hooks/useValidtor';

  interface Props {
    dbType: DBTypes;
    bizId: number;
  }

  interface Emits {
    (e: 'change', value: number[]): void;
    (e: 'remove'): void;
  }

  interface Exposes {
    getValue: () => Promise<number[]>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<number[]>({
    default: [],
  });

  const { t } = useI18n();

  const rules = [
    {
      validator: (value: number[]) => value.length > 0,
      message: t('至少选择一个集群'),
    },
  ];

  const { message: errorMessage, validator } = useValidtor(rules);

  const queryClusterTypes = {
    [DBTypes.MYSQL]: [ClusterTypes.TENDBSINGLE, ClusterTypes.TENDBHA].join(','),
    [DBTypes.TENDBCLUSTER]: ClusterTypes.TENDBCLUSTER,
    [DBTypes.REDIS]: [
      ClusterTypes.REDIS,
      ClusterTypes.PREDIXY_REDIS_CLUSTER,
      ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
      ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
      ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
      ClusterTypes.TWEMPROXY_TENDISPLUS_INSTANCE,
      ClusterTypes.REDIS_INSTANCE,
      ClusterTypes.TENDIS_SSD_INSTANCE,
      ClusterTypes.TENDIS_PLUS_INSTANCE,
      ClusterTypes.REDIS_CLUSTER,
      ClusterTypes.TENDIS_PLUS_CLUSTER,
    ].join(','),
    [DBTypes.MONGODB]: [ClusterTypes.MONGODB, ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER].join(
      ',',
    ),
    [DBTypes.SQLSERVER]: [ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE].join(','),
    [DBTypes.ES]: ClusterTypes.ES,
    [DBTypes.KAFKA]: ClusterTypes.KAFKA,
    [DBTypes.HDFS]: ClusterTypes.HDFS,
    [DBTypes.RIAK]: ClusterTypes.RIAK,
    [DBTypes.PULSAR]: ClusterTypes.PULSAR,
    [DBTypes.INFLUXDB]: ClusterTypes.INFLUXDB,
    [DBTypes.DORIS]: ClusterTypes.DORIS,
  };

  const { run: fetchData, data: clusterList } = useRequest(queryAllTypeCluster, {
    manual: true,
  });

  watch(
    () => props.bizId,
    () => {
      if (props.bizId) {
        fetchData({
          bk_biz_id: props.bizId,
          cluster_types: queryClusterTypes[props.dbType as keyof typeof queryClusterTypes],
          phase: 'online',
          limit: -1,
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: number[]) => {
    validator(value);
    emits('change', value);
  };

  const handleRemove = () => {
    emits('remove');
  };

  defineExpose<Exposes>({
    getValue() {
      return validator(modelValue.value).then(() => Promise.resolve(modelValue.value));
    },
  });
</script>

<style lang="less" scoped>
  .is-error {
    :deep(.bk-select-tag) {
      background-color: #fff0f1 !important;
    }
  }
</style>
