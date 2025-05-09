<template>
  <span class="inline-block">
    <BkDropdown
      :popover-options="{
        clickContentAutoHide: true,
        hideIgnoreReference: true,
      }">
      <template #default="{ popoverShow }">
        <BkButton
          class="export-dropdown-button"
          :class="{ active: popoverShow }">
          {{ t('导出') }}
          <DbIcon type="up-big dropdown-button-icon" />
        </BkButton>
      </template>
      <template #content>
        <BkDropdownMenu>
          <BkDropdownItem @click="() => handleExport('all')">
            {{ isCluster ? t('所有集群') : t('所有实例') }}
          </BkDropdownItem>
          <BkDropdownItem
            v-bk-tooltips="{
              disabled: hasSelected,
              content: isCluster ? t('请选择集群') : t('请选择实例'),
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

  import { exportDorisClusterToExcel, exportDorisInstanceToExcel } from '@services/source/doris';
  import { exportEsClusterToExcel, exportEsInstanceToExcel } from '@services/source/es';
  import { exportHdfsClusterToExcel, exportHdfsInstanceToExcel } from '@services/source/hdfs';
  import { exportInfluxdbClusterToExcel, exportInfluxdbInstanceToExcel } from '@services/source/influxdb';
  import { exportKafkaClusterToExcel, exportKafkaInstanceToExcel } from '@services/source/kafka';
  import { exportMongodbClusterToExcel, exportMongodbInstanceToExcel } from '@services/source/mongodb';
  import { exportPulsarClusterToExcel, exportPulsarInstanceToExcel } from '@services/source/pulsar';
  import { exportRedisClusterToExcel, exportRedisInstanceToExcel } from '@services/source/redis';
  import { exportRiakClusterToExcel, exportRiakInstanceToExcel } from '@services/source/riak';
  import {
    exportSqlServerHaClusterToExcel,
    exportSqlServerHaInstanceToExcel,
  } from '@services/source/sqlserveHaCluster';
  import { exportSqlServerSingleClusterToExcel } from '@services/source/sqlserverSingleCluster';
  import { exportTendbclusterInstanceToExcel, exportTendbclusterToExcel } from '@services/source/tendbcluster';
  import { exportTendbhaClusterToExcel, exportTendbhaInstanceToExcel } from '@services/source/tendbha';
  import { exportTendbsingleClusterToExcel, exportTendbsingleInstanceToExcel } from '@services/source/tendbsingle';

  interface Props {
    exportType?: 'cluster' | 'instance';
    ids?: number[];
    type:
      | 'tendbsingle'
      | 'tendbha'
      | 'spider'
      | 'redis'
      | 'pulsar'
      | 'kafka'
      | 'influxdb'
      | 'hdfs'
      | 'es'
      | 'riak'
      | 'mongodb'
      | 'sqlserver_ha'
      | 'sqlserver_single'
      | 'doris';
  }

  const props = withDefaults(defineProps<Props>(), {
    exportType: 'cluster',
    ids: undefined,
  });

  const { t } = useI18n();

  const hasSelected = computed(() => props.ids && props.ids.length > 0);

  const isCluster = props.exportType === 'cluster';

  const apiMap = {
    doris: {
      cluster: exportDorisClusterToExcel,
      instance: exportDorisInstanceToExcel,
    },
    es: {
      cluster: exportEsClusterToExcel,
      instance: exportEsInstanceToExcel,
    },
    hdfs: {
      cluster: exportHdfsClusterToExcel,
      instance: exportHdfsInstanceToExcel,
    },
    influxdb: {
      cluster: exportInfluxdbClusterToExcel,
      instance: exportInfluxdbInstanceToExcel,
    },
    kafka: {
      cluster: exportKafkaClusterToExcel,
      instance: exportKafkaInstanceToExcel,
    },
    mongodb: {
      cluster: exportMongodbClusterToExcel,
      instance: exportMongodbInstanceToExcel,
    },
    pulsar: {
      cluster: exportPulsarClusterToExcel,
      instance: exportPulsarInstanceToExcel,
    },
    redis: {
      cluster: exportRedisClusterToExcel,
      instance: exportRedisInstanceToExcel,
    },
    riak: {
      cluster: exportRiakClusterToExcel,
      instance: exportRiakInstanceToExcel,
    },
    spider: {
      cluster: exportTendbclusterToExcel,
      instance: exportTendbclusterInstanceToExcel,
    },
    sqlserver_ha: {
      cluster: exportSqlServerHaClusterToExcel,
      instance: exportSqlServerHaInstanceToExcel,
    },
    sqlserver_single: {
      cluster: exportSqlServerSingleClusterToExcel,
    },
    tendbha: {
      cluster: exportTendbhaClusterToExcel,
      instance: exportTendbhaInstanceToExcel,
    },
    tendbsingle: {
      cluster: exportTendbsingleClusterToExcel,
      instance: exportTendbsingleInstanceToExcel,
    },
  };

  const handleExport = async (type: 'all' | 'selected') => {
    if (!apiMap[props.type]) {
      return;
    }
    if (type === 'selected' && !hasSelected.value) {
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
    color: #c4c6cc !important;
  }
</style>
