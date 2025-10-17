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
    <InfoItem :label="t('DB类型')">
      {{ ticketDetails.details.group }}
    </InfoItem>
    <InfoItem :label="t('前置单据')">
      <BkButton
        text
        theme="primary"
        @click="handleGoTicketDetail">
        {{ ticketDetails.details.parent_ticket }}
      </BkButton>
    </InfoItem>
    <InfoItem :label="t('已下架主机')">
      <PrimaryTable
        :data="ticketDetails.details.recycle_hosts"
        row-key="bk_host_id">
        <TableColumn
          col-key="ip"
          fixed="left"
          :min-width="150"
          title="IP">
          <template #title>
            <div class="ip-header">
              IP
              <DbIcon
                type="copy"
                @click="copyAllIp" />
            </div>
          </template>
        </TableColumn>
        <TableColumn
          col-key="bk_cloud_name"
          :min-width="120"
          :title="t('管控区域')" />
        <TableColumn
          col-key="status"
          :min-width="120"
          :title="t('Agent 状态')">
          <template #default="{ row }: { row: RowData }">
            <HostAgentStatus :data="row.status" />
          </template>
        </TableColumn>
        <TableColumn
          col-key="city"
          :min-width="120"
          :title="t('地域')">
          <template #default="{ row }: { row: RowData }">
            {{ row.city || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="sub_zone"
          :min-width="120"
          :title="t('园区')">
          <template #default="{ row }: { row: RowData }">
            {{ row.sub_zone || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="rack_id"
          :min-width="120"
          :title="t('机架')">
          <template #default="{ row }: { row: RowData }">
            {{ row.rack_id || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="bk_os_name"
          :min-width="120"
          :title="t('操作系统')">
          <template #default="{ row }: { row: RowData }">
            {{ row.bk_os_name || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="device_class"
          :min-width="120"
          :title="t('机型')">
          <template #default="{ row }: { row: RowData }">
            {{ row.device_class || '--' }}
          </template>
        </TableColumn>
      </PrimaryTable>
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TicketModel, { type Common } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import HostAgentStatus from '@components/host-agent-status/Index.vue';

  import { execCopy, getBusinessHref } from '@utils';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Common.ResourcePoolRecycle>;
  }

  type RowData = Props['ticketDetails']['details']['recycle_hosts'][number];

  defineOptions({
    name: TicketTypes.RECYCLE_OLD_HOST,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();
  const router = useRouter();

  const handleGoTicketDetail = () => {
    const { href } = router.resolve({
      name: 'bizTicketManage',
      params: {
        ticketId: props.ticketDetails.details.parent_ticket,
      },
    });
    window.open(getBusinessHref(href, props.ticketDetails.bk_biz_id), '_blank');
  };

  const copyAllIp = () => {
    const ips = props.ticketDetails.details.recycle_hosts.map((item) => item.ip);
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
