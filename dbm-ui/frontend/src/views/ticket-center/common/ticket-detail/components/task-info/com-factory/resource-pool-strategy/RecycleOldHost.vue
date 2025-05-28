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
      <BkTable :data="ticketDetails.details.recycle_hosts">
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
          field="city"
          :label="t('地域')"
          :min-width="120">
          <template #default="{ data }: { data: RowData }">
            {{ data.city || '--' }}
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
          field="device_class"
          :label="t('机型')"
          :min-width="120">
          <template #default="{ data }: { data: RowData }">
            {{ data.device_class || '--' }}
          </template>
        </BkTableColumn>
      </BkTable>
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
