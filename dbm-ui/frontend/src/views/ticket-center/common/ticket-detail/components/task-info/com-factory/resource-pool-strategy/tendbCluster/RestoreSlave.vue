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
    :data="ticketDetails.details.infos"
    :show-overflow="false">
    <BkTableColumn
      :label="t('目标从库主机')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{ data.old_nodes.old_slave?.[0].ip }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('从库主机关联实例')"
      :min-width="180">
      <template #default="{ data }: { data: RowData }">
        <p
          v-for="item in relatedInfoMap[data.old_nodes.old_slave[0].ip]"
          :key="item.instance_address">
          {{ item.instance_address }}
        </p>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('同机关联集群')"
      :min-width="220">
      <template #default="{ data }: { data: RowData }">
        <p
          v-for="item in relatedInfoMap[data.old_nodes.old_slave[0].ip]"
          :key="item.master_domain">
          {{ item.master_domain }}
        </p>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('当前资源规格')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{ relatedInfoMap[data.old_nodes.old_slave?.[0].ip]?.[0]?.spec_config.name }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('新从库主机')"
      :min-width="150">
      <template #default>
        {{ t('资源池自动匹配') }}
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('备份源')">
      {{ backupSourceMap[ticketDetails.details.backup_source] }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';
  import { checkInstance } from '@services/source/dbbase';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.ResourcePool.RestoreSlave>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_RESTORE_SLAVE,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const backupSourceMap = {
    local: t('本地备份'),
    remote: t('远程备份'),
  };

  const relatedInfoMap = reactive<Record<string, ServiceReturnType<typeof checkInstance>>>({});

  useRequest(checkInstance, {
    defaultParams: [
      {
        bk_biz_id: props.ticketDetails.bk_biz_id,
        instance_addresses: props.ticketDetails.details.infos.map((item) => item.old_nodes.old_slave[0].ip),
      },
    ],
    onSuccess: (data) => {
      data.forEach((item) => {
        Object.assign(relatedInfoMap, {
          [item.ip]: [...(relatedInfoMap[item.ip] || []), item],
        });
      });
    },
  });
</script>
