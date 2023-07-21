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
  <div class="ticket-details">
    <BkLoading
      :loading="state.isLoading"
      style="min-height: 200px;">
      <template v-if="state.ticketData">
        <DbCard
          mode="collapse"
          :title="$t('基本信息')">
          <EditInfo
            :columns="baseColumns"
            :data="state.ticketData"
            width="30%" />
        </DbCard>
        <DbCard
          v-model:collapse="demandCollapse"
          :class="{'is-fullscreen': isFullscreen}"
          mode="collapse"
          :title="$t('需求信息')">
          <Component
            :is="detailsComp"
            :key="state.ticketData.id"
            :ticket-details="state.ticketData" />
        </DbCard>
        <slot
          :data="state.ticketData"
          name="flows" />
      </template>
    </BkLoading>
  </div>
</template>

<script setup lang="tsx">
  import { format } from 'date-fns';
  import { useI18n } from 'vue-i18n';

  import { getTicketDetails } from '@services/ticket';

  import { TicketTypes } from '@common/const';

  import CostTimer from '@components/cost-timer/CostTimer.vue';
  import EditInfo, { type InfoColumn } from '@components/editable-info/index.vue';

  import { useTimeoutPoll } from '@vueuse/core';

  import {
    getTagTheme,
    needPollStatus,
    StatusTypes,    type StatusTypesStrings  } from '../common/utils';

  import BigDataExpansionCapacity from './bigdata/BigDataExpansionCapacity.vue';
  import BigDataReboot from './bigdata/BigDataReboot.vue';
  import BigDataReplace from './bigdata/BigDataReplace.vue';
  import DetailsES from './bigdata/DetailsES.vue';
  import DetailsHDFS from './bigdata/DetailsHDFS.vue';
  import DetailsInfluxDB from './bigdata/DetailsInfluxDB.vue';
  import DetailsKafka from './bigdata/DetailsKafka.vue';
  import DetailsPulsar from './bigdata/DetailsPulsar.vue';
  import DetailsClusterOperation from './DetailsClusterOperation.vue';
  import InfluxdbOperations from './influxdb/InfluxdbOperations.vue';
  import InfluxdbReplace from './influxdb/InfluxdbReplace.vue';
  import DetailsMySQL from './mysql/DetailsMySQL.vue';
  import MySQLChecksum from './mysql/MySQLChecksum.vue';
  import MySQLClone from './mysql/MySQLClone.vue';
  import MySQLClusterOperation from './mysql/MySQLClusterOperation.vue';
  import MySQLFlashback from './mysql/MySQLFlashback.vue';
  import MySQLFullBackup from './mysql/MySQLFullBackup.vue';
  import MySQLHATruncate from './mysql/MySQLHATruncate.vue';
  import MySQLImportSQLFile from './mysql/MySQLImportSQLFile.vue';
  import MySQLMasterFailOver from './mysql/MySQLMasterFailOver.vue';
  import MySQLMasterSlaveSwitch from './mysql/MySQLMasterSlaveSwitch.vue';
  import MySQLMigrateCluster from './mysql/MySQLMigrateCluster.vue';
  import MySQLOperation from './mysql/MySQLOperation.vue';
  import MySQLProxyAdd from './mysql/MySQLProxyAdd.vue';
  import MySQLProxySwitch from './mysql/MySQLProxySwitch.vue';
  import MySQLRename from './mysql/MySQLRename.vue';
  import MySQLRestoreSlave from './mysql/MySQLRestoreSlave.vue';
  import MySQLRollbackCluster from './mysql/MySQLRollbackCluster.vue';
  import MySQLSlave from './mysql/MySQLSlave.vue';
  import MySQLTableBackup from './mysql/MySQLTableBackup.vue';
  import DetailsRedis from './redis/DetailsRedis.vue';
  import RedisOperation from './redis/RedisOperation.vue';
  import DetailsSpider from './spider/DetailsSpider.vue';

  const props = defineProps({
    data: {
      type: Object,
      required: true,
    },
    isTodos: {
      type: Boolean,
      default: false,
    },
  });

  const currentScope = getCurrentScope();
  const { t } = useI18n();
  const route = useRoute();

  const state = reactive({
    isLoading: false,
    ticketData: null as any,
  });
  const isFullscreen = computed(() => route.query.isFullscreen);
  const demandCollapse = ref(false);
  // 轮询
  const { isActive, resume, pause } = useTimeoutPoll(() => {
    fetchTicketDetails(props.data.id, true);
  }, 10000);
  const redisKeysType = [
    TicketTypes.REDIS_KEYS_EXTRACT,
    TicketTypes.REDIS_KEYS_DELETE,
    TicketTypes.REDIS_BACKUP,
    TicketTypes.REDIS_PURGE,
  ] as string[];
  const mysqlTicketType = [
    TicketTypes.MYSQL_AUTHORIZE_RULES,
    TicketTypes.MYSQL_EXCEL_AUTHORIZE_RULES,
  ] as string[];
  const clusterTicketType = [
    TicketTypes.REDIS_PROXY_CLOSE,
    TicketTypes.REDIS_PROXY_OPEN,
    TicketTypes.REDIS_DESTROY,
    TicketTypes.ES_DISABLE,
    TicketTypes.ES_DESTROY,
    TicketTypes.ES_ENABLE,
    TicketTypes.HDFS_ENABLE,
    TicketTypes.HDFS_DISABLE,
    TicketTypes.HDFS_DESTROY,
    TicketTypes.KAFKA_ENABLE,
    TicketTypes.KAFKA_DISABLE,
    TicketTypes.KAFKA_DESTROY,
    TicketTypes.PULSAR_ENABLE,
    TicketTypes.PULSAR_DISABLE,
    TicketTypes.PULSAR_DESTROY,
  ] as string[];

  const mysqlClusterTicketType = [
    TicketTypes.MYSQL_HA_DISABLE,
    TicketTypes.MYSQL_SINGLE_DISABLE,
    TicketTypes.MYSQL_HA_ENABLE,
    TicketTypes.MYSQL_SINGLE_ENABLE,
    TicketTypes.MYSQL_HA_DESTROY,
    TicketTypes.MYSQL_SINGLE_DESTROY,
  ] as string[];

  const bigDataReplaceType = [
    TicketTypes.ES_REPLACE,
    TicketTypes.HDFS_REPLACE,
    TicketTypes.KAFKA_REPLACE,
    TicketTypes.PULSAR_REPLACE,
  ] as string[];

  const mysqlSlaveType = [
    TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE,
    TicketTypes.MYSQL_ADD_SLAVE,
  ] as string[];

  const bigDataRebootType = [
    TicketTypes.HDFS_REBOOT,
    TicketTypes.ES_REBOOT,
    TicketTypes.KAFKA_REBOOT,
    TicketTypes.PULSAR_REBOOT,
  ] as string[];

  const bigDataCapacityType = [
    TicketTypes.ES_SCALE_UP,
    TicketTypes.ES_SHRINK,
    TicketTypes.HDFS_SCALE_UP,
    TicketTypes.HDFS_SHRINK,
    TicketTypes.KAFKA_SCALE_UP,
    TicketTypes.KAFKA_SHRINK,
    TicketTypes.PULSAR_SHRINK,
    TicketTypes.PULSAR_SCALE_UP,
  ] as string[];

  const mysqlClones: string[] = [TicketTypes.MYSQL_CLIENT_CLONE_RULES, TicketTypes.MYSQL_INSTANCE_CLONE_RULES];

  // 不同集群详情组件
  const detailsComp = computed(() => {
    // redis 申请单据
    if (state.ticketData.ticket_type === TicketTypes.TENDBCLUSTER_APPLY) {
      return DetailsSpider;
    }
    // redis 申请单据
    if (state.ticketData.ticket_type === TicketTypes.REDIS_CLUSTER_APPLY) {
      return DetailsRedis;
    }
    // Redis、大数据启停删单据
    if (clusterTicketType.includes(state.ticketData.ticket_type)) {
      return DetailsClusterOperation;
    }
    // 大数据替换单据
    if (bigDataReplaceType.includes(state.ticketData.ticket_type)) {
      return BigDataReplace;
    }
    if (redisKeysType.includes(state.ticketData.ticket_type)) {
      return RedisOperation;
    }
    if (mysqlTicketType.includes(state.ticketData.ticket_type)) {
      return MySQLOperation;
    }
    if (state.ticketData.ticket_type === TicketTypes.ES_APPLY) {
      return DetailsES;
    }
    if (state.ticketData.ticket_type === TicketTypes.HDFS_APPLY) {
      return DetailsHDFS;
    }
    if (state.ticketData.ticket_type === TicketTypes.KAFKA_APPLY) {
      return DetailsKafka;
    }
    // MySQL权限克隆
    if (mysqlClones.includes(state.ticketData.ticket_type)) {
      return MySQLClone;
    }
    // MySQL Slave
    if (mysqlSlaveType.includes(state.ticketData.ticket_type)) {
      return MySQLSlave;
    }
    // MySQL 重命名
    if (state.ticketData.ticket_type === TicketTypes.MYSQL_HA_RENAME_DATABASE) {
      return MySQLRename;
    }
    // 大数据实例重启
    if (bigDataRebootType.includes(state.ticketData.ticket_type)) {
      return BigDataReboot;
    }
    // MySQL 替换 PROXY
    if (state.ticketData.ticket_type === TicketTypes.MYSQL_PROXY_SWITCH) {
      return MySQLProxySwitch;
    }
    // MySQL 库表备份
    if (state.ticketData.ticket_type === TicketTypes.MYSQL_HA_DB_TABLE_BACKUP) {
      return MySQLTableBackup;
    }
    // MySQL 高可用清档
    if (state.ticketData.ticket_type === TicketTypes.MYSQL_HA_TRUNCATE_DATA) {
      return MySQLHATruncate;
    }
    // MySQL 克隆主从
    if (state.ticketData.ticket_type === TicketTypes.MYSQL_MIGRATE_CLUSTER) {
      return MySQLMigrateCluster;
    }
    // MySQL 主从互换
    if (state.ticketData.ticket_type === TicketTypes.MYSQL_MASTER_SLAVE_SWITCH) {
      return MySQLMasterSlaveSwitch;
    }
    // MySQL 新增 Proxy
    if (state.ticketData.ticket_type === TicketTypes.MYSQL_PROXY_ADD) {
      return MySQLProxyAdd;
    }
    // MySQL 主故障切换
    if (state.ticketData.ticket_type === TicketTypes.MYSQL_MASTER_FAIL_OVER) {
      return MySQLMasterFailOver;
    }
    // MySQL SQL变更执行
    if (state.ticketData.ticket_type === TicketTypes.MYSQL_IMPORT_SQLFILE) {
      return MySQLImportSQLFile;
    }
    // MySQL 闪回
    if (state.ticketData.ticket_type === TicketTypes.MYSQL_FLASHBACK) {
      return MySQLFlashback;
    }
    // MySQL 启停删
    if (mysqlClusterTicketType.includes(state.ticketData.ticket_type)) {
      return MySQLClusterOperation;
    }
    // MySQL 定点回档
    if (state.ticketData.ticket_type === TicketTypes.MYSQL_ROLLBACK_CLUSTER) {
      return MySQLRollbackCluster;
    }
    // MySQL SLAVE重建
    if (state.ticketData.ticket_type === TicketTypes.MYSQL_RESTORE_SLAVE) {
      return MySQLRestoreSlave;
    }
    // MySQL 全库备份
    if (state.ticketData.ticket_type === TicketTypes.MYSQL_HA_FULL_BACKUP) {
      return MySQLFullBackup;
    }
    // MySQL 校验
    if (state.ticketData.ticket_type === TicketTypes.MYSQL_CHECKSUM) {
      return MySQLChecksum;
    }
    // 大数据扩缩容
    if (bigDataCapacityType.includes(state.ticketData.ticket_type)) {
      return BigDataExpansionCapacity;
    }
    // Pulsar 上架
    if (state.ticketData.ticket_type === TicketTypes.PULSAR_APPLY) {
      return DetailsPulsar;
    }
    // influxdb 上架
    if (state.ticketData.ticket_type === TicketTypes.INFLUXDB_APPLY) {
      return DetailsInfluxDB;
    }
    // influxdb 禁用/重启/启用/删除
    if (
      [
        TicketTypes.INFLUXDB_DISABLE,
        TicketTypes.INFLUXDB_REBOOT,
        TicketTypes.INFLUXDB_ENABLE,
        TicketTypes.INFLUXDB_DESTROY,
      ].includes(state.ticketData.ticket_type)
    ) {
      return InfluxdbOperations;
    }
    // influxdb 替换
    if (state.ticketData.ticket_type === TicketTypes.INFLUXDB_REPLACE) {
      return InfluxdbReplace;
    }

    return DetailsMySQL;
  });

  /**
   * 基础信息配置
   */
  const baseColumns: InfoColumn[][] = [
    [{
      label: t('单号'),
      key: 'id',
    }, {
      label: t('单据类型'),
      key: 'ticket_type_display',
    }],
    [{
      label: t('单据状态'),
      key: 'status',
      render: () => {
        const value = state.ticketData.status as StatusTypesStrings;
        return <bk-tag theme={getTagTheme(value)}>{t(StatusTypes[value])}</bk-tag>;
      },
    }, {
      label: t('申请人'),
      key: 'creator',
    }],
    [{
      label: t('已耗时'),
      key: 'cost_time',
      render: () => <CostTimer value={state.ticketData?.cost_time || 0} isTiming={state.ticketData?.status === 'RUNNING'} />,
    }, {
      label: t('申请时间'),
      key: 'create_at',
      render: () => (state.ticketData.create_at ? format(new Date(state.ticketData.create_at), 'yyyy-MM-dd HH:mm:ss') : ''),
    }],
  ];

  /**
   * 获取单据详情
   */
  const fetchTicketDetails = (id: number, isPoll = false) => {
    state.isLoading = !isPoll;
    const params: Record<string, any> = {};
    if (props.isTodos) {
      params.is_reviewed = 1;
    }
    getTicketDetails(id, params)
      .then((res) => {
        state.ticketData = res;
        // 设置轮询
        if (currentScope?.active) {
          !isActive.value && needPollStatus.includes(state.ticketData?.status) && resume();
        } else {
          pause();
        }
      })
      .catch(() => {
        state.ticketData = null;
      })
      .finally(() => {
        state.isLoading = false;
      });
  };

  watch(() => props.data.id, (id: number) => {
    if (id) {
      state.ticketData = null;
      fetchTicketDetails(id);
    }
  }, { immediate: true });

  watch(isFullscreen, (isFullscreen) => {
    if (isFullscreen) {
      demandCollapse.value = true;
    }
  }, { immediate: true });
</script>

<style lang="less" scoped>
  .ticket-details {
    padding: 24px;

    .db-card {
      margin-bottom: 16px;

      &.is-fullscreen {
        position: fixed;
        top: 0;
        right: 0;
        z-index: 9999;
        width: 100%;
        height: 100%;
      }
    }
  }
</style>
