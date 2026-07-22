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
  <div>
    <InfoList>
      <InfoItem :label="t('目标选择模式')">
        {{ modeTextMap[targetSelectMode] }}
      </InfoItem>
      <InfoItem :label="t('强制重启')">
        {{ ticketDetails.details.force ? t('是') : t('否') }}
      </InfoItem>
    </InfoList>

    <!-- 按集群模式展示 -->
    <template v-if="targetSelectMode === 'cluster'">
      <TicketInfoTable
        :data="ticketDetails.details.infos"
        row-key="cluster_id">
        <TicketInfoTableColumn
          col-key="cluster_id"
          :get-copy-value="(row) => ticketDetails.details.clusters[row.cluster_id].immute_domain"
          :title="t('目标集群')">
          <template #default="{ row }: { row: {  cluster_id: number} }">
            {{ ticketDetails.details.clusters?.[row.cluster_id]?.immute_domain || '--' }}
          </template>
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="cluster_type"
          :title="t('集群类型')">
          <template #default="{ row }: { row: { cluster_id: number }}">
            {{ ticketDetails.details.clusters?.[row.cluster_id]?.cluster_type_name || '--' }}
          </template>
        </TicketInfoTableColumn>
      </TicketInfoTable>
    </template>

    <!-- 按主机模式展示 -->
    <template v-if="targetSelectMode === 'machine'">
      <TicketInfoTable
        :data="ticketDetails.details.infos"
        row-key="bk_host_id">
        <TicketInfoTableColumn
          col-key="bk_host_id"
          :get-copy-value="(row: { ip: string }) => row.ip"
          :title="t('主机IP')">
          <template #default="{ row }: { row: { ip: string } }">
            {{ row.ip || '--' }}
          </template>
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="cluster_type"
          :title="t('所属集群')">
          <template #default="{ row }: { row: { related_clusters: string[] }}">
            <div
              v-for="item in row.related_clusters"
              :key="item">
              <p>{{ item }}</p>
            </div>
          </template>
        </TicketInfoTableColumn>
      </TicketInfoTable>
    </template>

    <!-- 按实例模式展示（保持原有逻辑） -->
    <template v-if="targetSelectMode === 'instance'">
      <TicketInfoTable
        :data="ticketDetails.details.infos"
        row-key="instance_id">
        <TicketInfoTableColumn
          col-key="instance_id"
          :get-copy-value="(row) => ticketDetails.details.instances?.[row.instance_id]?.instance || ''"
          :title="t('实例')"
          width="300">
          <template #default="{ row }: { row: { instance_id: number } }">
            {{ ticketDetails.details.instances?.[row.instance_id]?.instance || '--' }}
          </template>
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="role"
          :title="t('角色')"
          width="100" />
        <TicketInfoTableColumn
          col-key="immute_domain"
          :title="t('所属集群')">
          <template #default="{ row }: { row: { cluster_id: number }}">
            {{ ticketDetails.details.clusters?.[row.cluster_id]?.immute_domain || '--' }}
          </template>
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="status"
          :title="t('状态')">
          <template #default="{ row }: { row: { instance_id: number }}">
            <ClusterInstanceStatus :data="ticketDetails.details.instances?.[row.instance_id]?.status" />
          </template>
        </TicketInfoTableColumn>
      </TicketInfoTable>
    </template>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  defineOptions({
    name: TicketTypes.MONGODB_INSTANCE_RELOAD,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  interface Props {
    ticketDetails: TicketModel<Mongodb.InstanceReload>;
  }

  const { t } = useI18n();

  // 目标模式文本映射
  const modeTextMap: Record<string, string> = {
    cluster: t('按集群'),
    instance: t('按实例'),
    machine: t('按主机'),
  };

  const targetSelectMode = props.ticketDetails.details.target_select_mode || 'instance';
</script>
