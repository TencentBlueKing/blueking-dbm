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
    :data="tableData"
    :merge-cells="mergeCells"
    :show-overflow="false">
    <BkTableColumn
      field="ip"
      :label="t('目标主机')" />
    <BkTableColumn
      field="role"
      :label="t('角色类型')" />
    <BkTableColumn
      field="cluster_domain"
      :label="t('所属集群')" />
    <BkTableColumn
      field="spec"
      :label="t('规格需求')">
      <template #default="{ data }: { data: RowData }">
        {{ data.spec?.name || '--' }}
        <SpecPanel
          v-if="data.spec"
          :data="data.spec"
          :hide-qps="!data.spec.qps.min">
          <DbIcon
            class="visible-icon ml-4"
            type="visible1" />
        </SpecPanel>
      </template>
    </BkTableColumn>
  </BkTable>
</template>

<script setup lang="ts">
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
    role: string;
    spec: SpecInfo;
  }

  const tableData = shallowRef<RowData[]>([]);
  const mergeCells = shallowRef<Array<{ col: number; colspan: number; row: number; rowspan: number }>>([]);

  watch(
    () => props.ticketDetails.details,
    () => {
      const { clusters, infos, specs } = props.ticketDetails.details;
      if (!infos.length) {
        return;
      }
      const domainCounter: Record<string, number> = {};
      infos.forEach((item) => {
        Object.entries(item.old_nodes).forEach(([role, hosts], index) => {
          const domain = clusters[item.cluster_ids[0]]?.immute_domain;
          tableData.value.push({
            cluster_domain: clusters[item.cluster_ids[0]]?.immute_domain || '--',
            ip: hosts[0].ip,
            role,
            spec: specs[hosts[0].spec_id] || {},
          });
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
      });
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less" scoped>
  .visible-icon {
    font-size: 16px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
