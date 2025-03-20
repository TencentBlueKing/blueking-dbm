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
  <InfoList>
    <InfoItem :label="t('迁移类型：')">
      {{ operaObjectMap[ticketDetails.details.opera_object] }}
    </InfoItem>
  </InfoList>
  <BkTable
    :data="ticketDetails.details.infos"
    :show-overflow="false">
    <BkTableColumn
      v-if="ticketDetails.details.opera_object === OperaObejctType.CLUSTER"
      :label="t('目标集群')">
      <template #default="{ data }: { data: RowData }">
        <div
          v-for="clusterId in data.cluster_ids"
          :key="clusterId"
          style="line-height: 20px">
          {{ ticketDetails.details.clusters[clusterId].immute_domain }}
        </div>
      </template>
    </BkTableColumn>
    <template v-else-if="ticketDetails.details.opera_object === OperaObejctType.MACHINE">
      <BkTableColumn
        :label="t('目标Master主机')"
        :min-width="150">
        <template #default="{ data }: { data: RowData }">
          {{ data.old_nodes.old_master[0].ip }}
        </template>
      </BkTableColumn>

      <BkTableColumn
        :label="t('同机关联实例')"
        :min-width="300">
        <template #default="{ data }: { data: RowData }">
          <p
            v-for="item in relatedInstances[data.old_nodes.old_master[0].ip]"
            :key="item">
            {{ item }}
          </p>
        </template>
      </BkTableColumn>

      <BkTableColumn
        :label="t('同机关联集群')"
        :min-width="300">
        <template #default="{ data }: { data: RowData }">
          <p
            v-for="item in relatedInstances[data.old_nodes.old_master[0].ip]"
            :key="item">
            {{ item }}
          </p>
        </template>
      </BkTableColumn>
    </template>
    <BkTableColumn
      :label="t('新主从主机')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        <div>
          <BkTag
            size="small"
            theme="success">
            M
          </BkTag>
          {{ data.resource_spec.new_master.hosts[0].ip }}
        </div>
        <div>
          <BkTag
            size="small"
            theme="info">
            S
          </BkTag>
          {{ data.resource_spec.new_slave.hosts[0].ip }}
        </div>
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('备份源')">
      {{ ticketDetails.details.backup_source === 'local' ? t('本地备份') : t('远程备份') }}
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';
  import { checkInstance } from '@services/source/dbbase';
  import { OperaObejctType } from '@services/types';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.ResourcePool.MigrateCluster>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.MYSQL_MIGRATE_CLUSTER,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const operaObjectMap = {
    [OperaObejctType.CLUSTER]: t('集群迁移'),
    [OperaObejctType.MACHINE]: t('整机迁移'),
  };

  const relatedInstances = reactive<Record<string, string[]>>({});
  const relatedClusters = reactive<Record<string, string[]>>({});

  useRequest(checkInstance, {
    defaultParams: [
      {
        bk_biz_id: props.ticketDetails.bk_biz_id,
        instance_addresses: props.ticketDetails.details.infos.map((item) => item.old_nodes.old_master[0].ip),
      },
    ],
    onSuccess: (data) => {
      data.forEach((item) => {
        Object.assign(relatedInstances, {
          [item.ip]: [...(relatedInstances[item.ip] || []), item.instance_address],
        });
        Object.assign(relatedClusters, {
          [item.ip]: [...(relatedClusters[item.ip] || []), item.master_domain],
        });
      });
    },
  });
</script>
