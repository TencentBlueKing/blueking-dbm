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
  <PrimaryTable
    :data="ticketDetails.details.infos"
    row-key="cluster_id">
    <TableColumn
      fixed="left"
      :min-width="150"
      :title="t('目标主库主机')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.old_master.ip }}
      </template>
    </TableColumn>
    <TableColumn
      :min-width="200"
      :title="t('主库主机关联实例')">
      <template #default="{ row: data }: { row: RowData }">
        <template
          v-for="relateClusterItem in relateClusterMap[data.old_master.ip]"
          :key="relateClusterItem.instance_address">
          <div>{{ relateClusterItem.instance_address }}</div>
        </template>
        <template v-if="relateClusterMap[data.old_master.ip]?.length < 1">--</template>
        <div
          v-if="isRelateClusterLoading"
          class="rotate-loading"
          style="display: inline-block">
          <DbIcon
            svg
            type="sync-pending" />
        </div>
      </template>
    </TableColumn>
    <TableColumn
      :min-width="150"
      :title="t('目标从库主机')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.old_slave.ip }}
      </template>
    </TableColumn>
    <TableColumn
      :min-width="200"
      :title="t('从库主机关联实例')">
      <template #default="{ row: data }: { row: RowData }">
        <template
          v-for="relateClusterItem in relateClusterMap[data.old_slave.ip]"
          :key="relateClusterItem.instance_address">
          <div>{{ relateClusterItem.instance_address }}</div>
        </template>
        <template v-if="relateClusterMap[data.old_slave.ip]?.length < 1">--</template>
        <div
          v-if="isRelateClusterLoading"
          class="rotate-loading"
          style="display: inline-block">
          <DbIcon
            svg
            type="sync-pending" />
        </div>
      </template>
    </TableColumn>
    <TableColumn
      :min-width="200"
      :title="t('所属集群')">
      <template #default="{ row: data }: { row: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </TableColumn>
    <TableColumn
      fixed="right"
      :min-width="150"
      :title="t('新实例')">
      <template #default="{ row: data }: { row: RowData }">
        <div>
          <BkTag
            size="small"
            theme="info">
            {{ t('主') }}
          </BkTag>
          <span>{{ data.new_master.ip }}</span>
        </div>
        <div>
          <BkTag
            size="small"
            theme="success">
            {{ t('从') }}
          </BkTag>
          <span>{{ data.new_slave.ip }}</span>
        </div>
      </template>
    </TableColumn>
  </PrimaryTable>
  <InfoList>
    <InfoItem :label="t('备份源')">
      {{ ticketDetails.details.backup_source === 'local' ? t('本地备份') : t('远程备份') }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';
  import { checkInstance } from '@services/source/dbbase';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.MigrateCluster>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_MIGRATE_CLUSTER,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const relateClusterMap = shallowRef<Record<string, ServiceReturnType<typeof checkInstance>>>({});

  const { loading: isRelateClusterLoading } = useRequest(checkInstance, {
    defaultParams: [
      {
        bk_biz_id: props.ticketDetails.bk_biz_id,
        instance_addresses: _.flatten(
          props.ticketDetails.details.infos.map((item) => [item.old_master.ip, item.old_slave.ip]),
        ),
      },
    ],
    onSuccess(data) {
      data.forEach((item) => {
        if (!relateClusterMap.value[item.ip]) {
          relateClusterMap.value[item.ip] = [];
        }
        relateClusterMap.value[item.ip].push(item);
      });
    },
  });
</script>
