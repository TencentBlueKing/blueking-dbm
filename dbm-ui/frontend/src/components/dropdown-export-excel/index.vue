<template>
  <span class="inline-block ml-8">
    <BkDropdown
      @hide="() => isCopyDropdown = false"
      @show="() => isCopyDropdown = true">
      <BkButton
        class="export-dropdown-button"
        :class="{ 'active': isCopyDropdown }">
        {{ t('导出') }}
        <DbIcon type="up-big dropdown-button-icon" />
      </BkButton>
      <template #content>
        <BkDropdownMenu>
          <BkDropdownItem @click="() => handleExport('all')">
            {{ isCluster ? t('所有集群') : t('所有实例') }}
          </BkDropdownItem>
          <BkDropdownItem
            v-bk-tooltips="{
              disabled: hasSelected,
              content: isCluster ? t('请选择集群') : t('请选择实例')
            }"
            :ext-cls="!hasSelected ? 'export-dropdown-item-disable' : ''"
            @click="() => handleExport('selected')">
            {{ isCluster ? t('已选集群') : t('已选实例') }}
          </BkDropdownItem>
        </BkDropdownMenu>
      </template>
    </BkDropdown>
  </span>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import {
    exportEsClusterToExcel,
    exportEsInstanceToExcel,
  } from '@services/source/es';
  import {
    exportHdfsClusterToExcel,
    exportHdfsInstanceToExcel,
  } from '@services/source/hdfs';
  import {
    exportInfluxdbClusterToExcel,
    exportInfluxdbInstanceToExcel,
  } from '@services/source/influxdb';
  import {
    exportKafkaClusterToExcel,
    exportKafkaInstanceToExcel,
  } from '@services/source/kafka';
  import {
    exportPulsarClusterToExcel,
    exportPulsarInstanceToExcel,
  } from '@services/source/pulsar';
  import {
    exportRedisClusterToExcel,
    exportRedisInstanceToExcel,
  } from '@services/source/redis';
  import {
    exportRiakClusterToExcel,
    exportRiakInstanceToExcel,
  } from '@services/source/riak';
  import {
    exportSpiderClusterToExcel,
    exportSpiderInstanceToExcel,
  } from '@services/source/spider';
  import { exportSqlserverHaClusterToExcel } from '@services/source/sqlserveHaCluster';
  import { exportSqlserverSingleClusterToExcel } from '@services/source/sqlserverSingleCluster';
  import {
    exportTendbhaClusterToExcel,
    exportTendbhaInstanceToExcel,
  } from '@services/source/tendbha';
  import {
    exportTendbsingleClusterToExcel,
    exportTendbsingleInstanceToExcel,
  } from '@services/source/tendbsingle';

  interface Props {
    type: 'tendbsingle' | 'tendbha' | 'spider' | 'redis' | 'pulsar' | 'kafka' | 'influxdb' | 'hdfs' | 'es' | 'riak' | 'sqlserverha' | 'sqlserversingle';
    ids?: number[];
    exportType?: 'cluster' | 'instance';
    hasSelected?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    exportType: 'cluster',
    hasSelected: false,
    ids: undefined,
  });

  const { t } = useI18n();

  const isCopyDropdown = ref(false);

  const isCluster = props.exportType === 'cluster';

  const apiMap = {
    tendbsingle: {
      cluster: exportTendbsingleClusterToExcel,
      instance: exportTendbsingleInstanceToExcel,
    },
    tendbha: {
      cluster: exportTendbhaClusterToExcel,
      instance: exportTendbhaInstanceToExcel,
    },
    spider: {
      cluster: exportSpiderClusterToExcel,
      instance: exportSpiderInstanceToExcel,
    },
    redis: {
      cluster: exportRedisClusterToExcel,
      instance: exportRedisInstanceToExcel,
    },
    pulsar: {
      cluster: exportPulsarClusterToExcel,
      instance: exportPulsarInstanceToExcel,
    },
    kafka: {
      cluster: exportKafkaClusterToExcel,
      instance: exportKafkaInstanceToExcel,
    },
    influxdb: {
      cluster: exportInfluxdbClusterToExcel,
      instance: exportInfluxdbInstanceToExcel,
    },
    hdfs: {
      cluster: exportHdfsClusterToExcel,
      instance: exportHdfsInstanceToExcel,
    },
    es: {
      cluster: exportEsClusterToExcel,
      instance: exportEsInstanceToExcel,
    },
    riak: {
      cluster: exportRiakClusterToExcel,
      instance: exportRiakInstanceToExcel,
    },
    sqlserverha: {
      cluster: exportSqlserverHaClusterToExcel,
    },
    sqlserversingle: {
      cluster: exportSqlserverSingleClusterToExcel,
    },
  };

  const handleExport = async (type: 'all' | 'selected') => {
    if (!apiMap[props.type]) {
      return;
    }
    if (type === 'selected' && !props.hasSelected) {
      return;
    }
    if (isCluster) {
      // 导出集群
      const params = {
        cluster_ids: props.ids,
      };
      if (type === 'all') {
        // 导出所有
        delete params.cluster_ids;
      }
      await apiMap[props.type].cluster(params);
    } else {
      // 导出实例
      const params = {
        bk_host_ids: props.ids,
      };
      if (type === 'all') {
        // 导出所有
        delete params.bk_host_ids;
      }
      await apiMap[props.type].instance(params);
    }
  };


</script>

<style lang="less">
  .export-dropdown-button {
    .dropdown-button-icon {
      margin-left: 6px;
      transition: all 0.2s;
    }

    &.active:not(.is-disabled) {
      .dropdown-button-icon {
        transform: rotate(180deg);
      }
    }
  }

  .export-dropdown-item-disable {
    color: #C4C6CC !important;
  }
</style>
