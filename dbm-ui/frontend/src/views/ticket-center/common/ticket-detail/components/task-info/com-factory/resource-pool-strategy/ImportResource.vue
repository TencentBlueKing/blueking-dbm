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
    <InfoItem
      :label="t('导入主机')"
      style="flex: 1 0 100%">
      <TicketInfoTable
        :data="ticketDetails.details.hosts"
        ellipsis
        row-key="ip">
        <TicketInfoTableColumn
          col-key="ip"
          fixed="left"
          :get-copy-value="(row: RowData) => row.ip"
          :min-width="150"
          title="IP">
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="bk_cloud_name"
          :min-width="120"
          :title="t('管控区域')" />
        <TicketInfoTableColumn
          col-key="status"
          :min-width="120"
          :title="t('Agent 状态')">
          <template #default="{ row: data }: { row: RowData }">
            <HostAgentStatus :data="data.status" />
          </template>
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="city_name"
          :min-width="120"
          :title="t('地域')">
          <template #default="{ row: data }: { row: RowData }">
            {{ data.city_name || '--' }}
          </template>
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="sub_zone"
          :min-width="120"
          :title="t('园区')">
          <template #default="{ row: data }: { row: RowData }">
            {{ data.sub_zone || '--' }}
          </template>
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="rack_id"
          :min-width="120"
          :title="t('机架')">
          <template #default="{ row: data }: { row: RowData }">
            {{ data.rack_id || '--' }}
          </template>
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="bk_os_name"
          :min-width="120"
          :title="t('操作系统')">
          <template #default="{ row: data }: { row: RowData }">
            {{ data.bk_os_name || '--' }}
          </template>
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="svr_device_class"
          :min-width="120"
          :title="t('机型')">
          <template #default="{ row: data }: { row: RowData }">
            {{ data.svr_device_class || '--' }}
          </template>
        </TicketInfoTableColumn>
      </TicketInfoTable>
    </InfoItem>
    <InfoItem :label="t('所属业务')">
      {{
        ticketDetails.details.for_biz === 0
          ? t('公共资源池')
          : globalBizsStore.bizIdMap.get(ticketDetails.details.for_biz)?.name
      }}
    </InfoItem>
    <InfoItem :label="t('所属 DB 类型')">
      {{ resourceTypeDisplay() }}
    </InfoItem>
    <InfoItem
      :label="t('资源标签')"
      style="flex: 1 0 100%">
      <TagBlock :data="ticketDetails.details.label_names" />
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Common } from '@services/model/ticket/ticket';

  import { useGlobalBizs } from '@stores';

  import { DBTypeInfos, DBTypes, TicketTypes } from '@common/const';

  import HostAgentStatus from '@components/host-agent-status/Index.vue';
  import TagBlock from '@components/tag-block/Index.vue';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Common.ImportResource>;
  }

  type RowData = Props['ticketDetails']['details']['hosts'][number];

  defineOptions({
    name: TicketTypes.RESOURCE_IMPORT,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const resourceTypeDisplay = () => {
    const { resource_type: resourceType } = props.ticketDetails.details;
    if (!resourceType || resourceType === 'PUBLIC') {
      return t('通用');
    }
    if (resourceType === 'vm') {
      return 'Vm';
    }
    return DBTypeInfos[resourceType as DBTypes]?.name;
  };
</script>
<style lang="less" scoped>
  .ip-header {
    &:hover {
      [class*='db-icon'] {
        display: inline !important;
      }
    }

    [class*='db-icon'] {
      display: none;
      margin-top: 1px;
      margin-left: 4px;
      color: @primary-color;
      cursor: pointer;
    }
  }
</style>
