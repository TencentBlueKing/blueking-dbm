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
  <BkTable
    border
    :data="tableData"
    :merge-cells="mergeCells"
    :row-class-name="generateRowClass"
    :show-overflow="false">
    <BkTableColumn
      field="ip"
      :label="t('目标主机')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        <p class="has-related">{{ data.ip || '--' }}</p>
        <div
          v-if="data?.related_slave_ip"
          class="related-slave">
          <p>{{ t('关联 Slave') }}</p>
          <p>-- {{ data?.related_slave_ip }}</p>
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="role"
      :label="t('角色类型')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        <p class="has-related">{{ data.role || '--' }}</p>
        <p
          v-if="data?.related_slave_ip"
          class="has-related related-slave-cell">
          redis_slave
        </p>
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="cluster_domain"
      :label="t('所属集群')"
      :min-width="250">
      <template #default="{ data }: { data: RowData }">
        <p class="has-related">{{ data.cluster_domain || '--' }}</p>
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="spec_config"
      :label="t('规格需求')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        <div class="has-related">
          {{ data.spec_config?.name || '--' }}
          <SpecPanel
            v-if="data.spec_config?.name"
            :data="data.spec_config"
            :hide-qps="!data.spec_config.qps?.min">
            <DbIcon
              class="visible-icon ml-4"
              type="visible1" />
          </SpecPanel>
        </div>

        <div
          v-if="data.related_slave_spec?.name"
          class="has-related related-slave-cell">
          {{ data.related_slave_spec?.name || '--' }}
          <SpecPanel
            v-if="data.related_slave_spec?.name"
            :data="data.related_slave_spec"
            :hide-qps="!data.related_slave_spec.qps?.min">
            <DbIcon
              class="visible-icon ml-4"
              type="visible1" />
          </SpecPanel>
        </div>
      </template>
    </BkTableColumn>
  </BkTable>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import SpecPanel from '@components/render-table/columns/spec-display/Panel.vue';

  import type { SpecInfo } from '@views/db-manage/redis/common/spec-panel/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Redis.ResourcePool.ClusterCutoff>;
  }

  defineOptions({
    name: TicketTypes.REDIS_CLUSTER_CUTOFF,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  interface RowData {
    cluster_domain: string;
    ip: string;
    related_slave_ip?: string; // 关联的slave
    related_slave_spec?: SpecInfo; // 关联的slave
    role: string;
    spec_config: SpecInfo;
  }

  const mergeCells = shallowRef<Array<{ col: number; colspan: number; row: number; rowspan: number }>>([]);
  const ipInfoMap = reactive<Record<string, RowData>>({});
  const tableData = ref<RowData[]>([]);

  const generateRowClass = ({ row }: { row: RowData }) => {
    if (row.related_slave_ip) {
      return 'related-slave-row';
    }
    return '';
  };

  watch(
    () => props.ticketDetails.details,
    () => {
      const { clusters, infos, recycle_hosts: recycleHosts, specs } = props.ticketDetails.details;
      if (!infos.length || !recycleHosts.length) {
        return;
      }

      const generateData = (
        list: Redis.ResourcePool.ClusterCutoff['infos'][0]['redis_master'],
        role: keyof Redis.ResourcePool.ClusterCutoff['infos'][0]['old_nodes'],
        clusterIds: number[],
      ) => {
        if (list?.length) {
          _.uniqBy(list, 'ip').forEach((hostInfo) => {
            const clusterInfo = clusters[clusterIds[0]];
            const ip = hostInfo.master_ip || hostInfo.ip;
            const specId = hostInfo.master_spec_id || hostInfo.spec_id;
            if (!ipInfoMap[ip]) {
              Object.assign(ipInfoMap, {
                [ip]: {
                  cluster_domain: clusterInfo.immute_domain,
                  ip,
                  role,
                  spec_config: specs[specId],
                },
              });
            } else {
              ipInfoMap[ip].related_slave_ip = hostInfo.ip;
              ipInfoMap[ip].related_slave_spec = specs[specId];
            }
          });
        }
      };

      infos.forEach((infoItem) => {
        generateData(infoItem.old_nodes.redis_master, 'redis_master', infoItem.cluster_ids);
        generateData(infoItem.old_nodes.redis_slave, 'redis_slave', infoItem.cluster_ids);
        generateData(infoItem.old_nodes.proxy, 'proxy', infoItem.cluster_ids);
      });

      const list = Object.values(ipInfoMap);
      const domainCounter: Record<string, number> = {};
      list.forEach((rowData, index) => {
        const domain = rowData.cluster_domain;
        domainCounter[domain] = (domainCounter[domain] || 0) + 1;
        if (domainCounter[domain] > 1) {
          mergeCells.value.push({
            col: 2,
            colspan: 1,
            row: index + 1 - domainCounter[domain],
            rowspan: domainCounter[domain],
          });
        }
      });
      tableData.value = list;
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less">
  .visible-icon {
    font-size: 16px;
    color: #3a84ff;
    cursor: pointer;
  }

  .related-slave-row {
    td {
      height: 80px !important;
      padding: 0 !important;
    }

    .vxe-cell {
      padding: 0 !important;
    }

    .has-related {
      height: 40px;
      padding: 0 16px;
      line-height: 40px;
    }

    .related-slave {
      height: 40px;
      padding: 0 16px;
      line-height: 18px;
      color: #979ba5;
      background: #fafbfd;
    }

    .related-slave-cell {
      border-top: 1px solid #dcdee5;
    }
  }
</style>
