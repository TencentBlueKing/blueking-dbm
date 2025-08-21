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
      <BkTable :data="ticketDetails.details.hosts">
        <BkTableColumn
          field="ip"
          fixed="left"
          label="IP"
          :min-width="150">
          <template #header>
            <div class="ip-header">
              IP
              <DbIcon
                type="copy"
                @click="copyAllIp" />
            </div>
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="bk_cloud_name"
          :label="t('管控区域')"
          :min-width="120" />
        <BkTableColumn
          field="status"
          :label="t('Agent 状态')"
          :min-width="120">
          <template #default="{ data }: { data: RowData }">
            <HostAgentStatus :data="data.status" />
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="city_name"
          :label="t('地域')"
          :min-width="120">
          <template #default="{ data }: { data: RowData }">
            {{ data.city_name || '--' }}
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="sub_zone"
          :label="t('园区')"
          :min-width="120">
          <template #default="{ data }: { data: RowData }">
            {{ data.sub_zone || '--' }}
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="rack_id"
          :label="t('机架')"
          :min-width="120">
          <template #default="{ data }: { data: RowData }">
            {{ data.rack_id || '--' }}
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="bk_os_name"
          :label="t('操作系统')"
          :min-width="120">
          <template #default="{ data }: { data: RowData }">
            {{ data.bk_os_name || '--' }}
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="svr_device_class"
          :label="t('机型')"
          :min-width="120">
          <template #default="{ data }: { data: RowData }">
            {{ data.svr_device_class || '--' }}
          </template>
        </BkTableColumn>
      </BkTable>
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

  import { execCopy } from '@utils';

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

  const copyAllIp = () => {
    const ips = props.ticketDetails.details.hosts.map((item) => item.ip);
    if (ips.length > 0) {
      execCopy(ips.join('\n'), t('复制成功，共n条', { n: ips.length }));
    }
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
