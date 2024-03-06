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
  <BkLoading :loading="loading">
    <DbOriginalTable
      :columns="columns"
      :data="tableData" />
  </BkLoading>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getMongoList } from '@services/source/mongodb';
  import type { TicketDetails } from '@services/types/ticket';

  interface ProxyScaleUpDetails {
    clusters: {
      [key: string]: {
        alias: string;
        bk_biz_id: number;
        bk_cloud_id: number;
        cluster_type: string;
        cluster_type_name: string;
        creator: string;
        disaster_tolerance_level: string;
        db_module_id: number;
        id: number;
        immute_domain: string;
        major_version: string;
        name: string;
        phase: string;
        region: string;
        status: string;
        tag: string[];
        time_zone: string;
        updater: string;
      };
    };
    infos: {
      cluster_id: number;
      resource_spec: {
        mongos: {
          count: number;
          spec_id: number;
        };
      };
      role: string;
    }[];
    is_safe: boolean;
    ip_source: string;
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
    ticketDetails: TicketDetails<ProxyScaleUpDetails>;
  }

  interface RowData {
    immute_domain: string;
    node_type: string;
    sepc_name: string;
    add_shard_num: number;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { clusters, infos, specs } = props.ticketDetails.details;

  const tableData = ref<RowData[]>([]);

  const columns = [
    {
      label: t('目标分片集群'),
      field: 'immute_domain',
      showOverflowTooltip: true,
    },
    {
      label: t('扩容节点类型'),
      field: 'node_type',
    },
    {
      label: t('扩容规格'),
      field: 'sepc_name',
      showOverflowTooltip: true,
    },
    {
      label: t('扩容至(台)'),
      field: 'add_shard_num',
    },
  ];

  const { loading, run: fetchMongoList } = useRequest(getMongoList, {
    manual: true,
    onSuccess(result) {
      const shardNumMap = result.results.reduce(
        (results, item) => {
          Object.assign(results, {
            [item.id]: item.shard_num,
          });
          return results;
        },
        {} as Record<number, number>,
      );
      tableData.value = infos.map((item) => ({
        immute_domain: clusters[item.cluster_id].immute_domain,
        node_type: 'mongos',
        sepc_name: specs[item.resource_spec.mongos.spec_id].name,
        add_shard_num: shardNumMap[item.cluster_id] + item.resource_spec.mongos.count,
      }));
    },
  });

  fetchMongoList({
    domains: props.ticketDetails.details.infos.map((item) => clusters[item.cluster_id].immute_domain).join(','),
  });
</script>
