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
  <DbOriginalTable
    class="details-backup__table"
    :columns="columns"
    :data="tableData" />
  <template v-if="tableSettingData.length > 0">
    <div class="ticket-details__info">
      <div class="ticket-details__list">
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ t('库表设置') }}：</span>
        </div>
      </div>
    </div>
    <DbOriginalTable
      class="details-backup__table"
      :columns="dbTableColumns"
      :data="tableSettingData" />
  </template>
  <div class="ticket-details__info">
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('构造新主机规格') }}：</span>
        <span class="ticket-details__item-value">
          {{ specs[resource_spec.mongodb.spec_id].name ?? '--' }}
        </span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('每台主机构造Shard数量') }}：</span>
        <span class="ticket-details__item-value">
          {{ instance_per_host }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { TicketDetails } from '@services/types/ticket';

  import { utcDisplayTime } from '@utils';

  interface DbStructDeatils  {
    apply_details: {
      infos: {
        bk_cloud_id: number;
        resource_spec: {
          mongo_machine_set: {
            count: number;
            set_id: string;
            spec_id: {
              count: number;
              spec_id: number;
            };
            affinity: string;
            group_count: number;
            location_spec: {
              city: string;
              sub_zone_ids: any[];
            };
          };
        };
      }[];
      spec_id: {
        count: number;
        spec_id: number;
      };
      city_code: string;
      ip_source: string;
      db_version: string;
      node_count: number;
      start_port: number;
      bk_cloud_id: number;
      db_app_abbr: string;
      cluster_type: string;
      replica_sets: {
        name: string;
        domain: string;
        set_id: string;
      }[];
      oplog_percent: number;
      replica_count: number;
      node_replica_count: number;
      disaster_tolerance_level: string;
    };
    backupinfo: {
      [clusterId: string]: {
        app: string;
        app_name: string;
        bs_status: string;
        bs_tag: string;
        bs_taskid: string;
        bk_biz_id: number;
        bk_cloud_id: number;
        cluster_domain: string;
        cluster_id: number;
        cluster_name: string;
        cluster_type: string;
        end_time: string;
        file_name: string;
        file_path: string;
        file_size: number;
        meta_role: string;
        my_file_num: number;
        pitr_binlog_index: number;
        pitr_date: string;
        pitr_file_type: string;
        pitr_fullname: string;
        pitr_last_pos: number;
        report_type: string;
        releate_bill_id: string;
        releate_bill_info: string;
        role_type: string;
        server_ip: string;
        server_port: number;
        set_name: string;
        src: string;
        start_time: string;
        total_file_num: number;
      };
    };
    cluster_ids: number[];
    cluster_type: string;
    clusters: {
      [clusterId: string]: {
        alias: string;
        bk_biz_id: number;
        bk_cloud_id: number;
        cluster_type: string;
        cluster_type_name: string;
        creator: string;
        db_module_id: number;
        disaster_tolerance_level: string;
        id: number;
        immute_domain: string;
        major_version: string;
        name: string;
        phase: string;
        region: string;
        status: string;
        tag: any[];
        time_zone: string;
        updater: string;
      };
    };
    city_code: string;
    instance_per_host: number;
    ns_filter?: {
      db_patterns: string[];
      ignore_dbs: string[];
      ignore_tables: string[];
      table_patterns: string[];
    };
    resource_spec: {
      mongodb: {
        count: number;
        spec_id: number;
      };
    };
    rollback_time: string;
    specs: {
      [key: string]: {
        cpu: {
          max: number;
          min: number;
        };
        device_class: string[];
        id: number;
        mem: {
          max: number;
          min: number;
        };
        name: string;
        qps: Record<string, unknown>;
        storage_spec: {
          mount_point: string;
          size: number;
          type: string;
        }[];
      };
    };
  }

  interface Props {
    ticketDetails: TicketDetails<DbStructDeatils>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const {
    clusters,
    cluster_ids: clusterIds,
    backupinfo,
    ns_filter: nsFilter,
    resource_spec,
    instance_per_host,
    rollback_time: rollbackTime,
    specs
  } = props.ticketDetails.details;

  const columns = [
    {
      label: t('集群'),
      field: 'immute_domain',
      showOverflowTooltip: true,
    },
    {
      label: t('构造类型'),
      field: 'struct_type',
      rowspan: clusterIds.length,
      showOverflowTooltip: true,
    },
    {
      label: t('备份文件'),
      field: 'backup_file',
    },
  ];

  if (!backupinfo) {
    columns[2] = {
      label: t('指定时间'),
      field: 'target_time',
    };
  }

  const dbTableColumns = [
    {
      label: t('备份DB名'),
      field: 'db_patterns',
      showOverflowTooltip: false,
      render: ({ cell }: { cell: string[] }) => (
        <div class="text-overflow" v-overflow-tips={{
            content: cell,
          }}>
          {cell.length > 0 ? cell.map(item => <bk-tag>{item}</bk-tag>) : '--'}
        </div>
      ),
    },
    {
      label: t('忽略DB名'),
      field: 'ignore_dbs',
      showOverflowTooltip: false,
      render: ({ cell }: { cell: string[] }) => (
        <div class="text-overflow" v-overflow-tips={{
            content: cell,
          }}>
          {cell.length > 0 ? cell.map(item => <bk-tag>{item}</bk-tag>) : '--'}
        </div>
      ),
    },
    {
      label: t('备份表名'),
      field: 'table_patterns',
      showOverflowTooltip: false,
      render: ({ cell }: { cell: string[] }) => (
        <div class="text-overflow" v-overflow-tips={{
            content: cell,
          }}>
          {cell.map(item => <bk-tag>{item}</bk-tag>)}
        </div>
      ),
    },
    {
      label: t('忽略表名'),
      field: 'ignore_tables',
      showOverflowTooltip: false,
      render: ({ cell }: { cell: string[] }) => (
        <div class="text-overflow" v-overflow-tips={{
            content: cell,
          }}>
          {cell.length > 0 ? cell.map(item => <bk-tag>{item}</bk-tag>) : '--'}
        </div>
      ),
    },
  ];

  const tableSettingData = nsFilter ? [{
    ...nsFilter,
  }] : [];


  const tableData = computed(() => clusterIds.map(id => ({
    immute_domain: clusters[id].immute_domain,
    struct_type: backupinfo ? t('备份记录') : t('回档至指定时间 '),
    backup_file: backupinfo ? `${backupinfo[id].role_type}${utcDisplayTime(backupinfo[id].end_time)}` : '',
    target_time: rollbackTime ? utcDisplayTime(rollbackTime) : '',
  }))
  )
</script>
<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
  @import '@views/tickets/common/styles/ticketDetails.less';

  .ticket-details {
    &__info {
      padding-left: 80px;
    }

    &__item {
      &-label {
        min-width: 0;
        text-align: left;
      }
    }
  }

  .details-backup {
    &__table {
      padding-left: 80px;
    }
  }
</style>
