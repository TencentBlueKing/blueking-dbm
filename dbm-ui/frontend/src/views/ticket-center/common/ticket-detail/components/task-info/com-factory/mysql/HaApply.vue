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
  <div class="info-title">{{ t('基本信息') }}</div>
  <InfoList>
    <InfoItem :label="t('所属业务')">
      {{ ticketDetails.bk_biz_name || '--' }}
    </InfoItem>
    <InfoItem :label="t('业务代号')">
      {{ ticketDetails.db_app_abbr || '--' }}
    </InfoItem>
    <InfoItem :label="t('DB模块名')">
      {{ ticketDetails.details.db_module_name || '--' }}
    </InfoItem>
  </InfoList>
  <RegionRequirements :details="ticketDetails.details" />
  <div class="info-title mt-20">{{ t('数据库部署信息') }}</div>
  <InfoList>
    <InfoItem :label="t('Proxy起始端口')">
      {{ ticketDetails.details.start_proxy_port || '--' }}
    </InfoItem>
    <InfoItem :label="t('MySQL起始端口')">
      {{ ticketDetails.details.start_mysql_port || '--' }}
    </InfoItem>
  </InfoList>
  <div class="info-title mt-20">{{ t('需求信息') }}</div>
  <InfoList>
    <InfoItem :label="t('数量')">
      {{ ticketDetails.details.cluster_count }}
    </InfoItem>
    <template v-if="ticketDetails.details.resource_spec?.proxy">
      <InfoItem :label="t('Proxy 存储资源规格')">
        <SpecDetailPopover
          :data="ticketDetails.details.resource_spec.proxy"
          placement="top">
          <span
            class="pb-2"
            style="cursor: pointer; border-bottom: 1px dashed #979ba5">
            {{ ticketDetails.details.resource_spec.proxy.spec_name }}（{{
              `${ticketDetails.details.resource_spec.proxy.count} ${t('台')}`
            }}）
          </span>
        </SpecDetailPopover>
      </InfoItem>
      <InfoItem :label="t('Proxy 存储资源标签')">
        <template v-if="ticketDetails.details.resource_spec.proxy.label_names?.length">
          <DbTag
            v-for="item in ticketDetails.details.resource_spec.proxy.label_names"
            :key="item">
            {{ item }}
          </DbTag>
        </template>
        <DbTag
          v-else
          theme="success">
          {{ t('通用无标签') }}
        </DbTag>
      </InfoItem>
    </template>
    <template v-if="ticketDetails.details.resource_spec?.backend_group">
      <InfoItem :label="t('后端存储资源规格')">
        <SpecDetailPopover
          :data="ticketDetails.details.resource_spec.backend_group"
          placement="top">
          <span
            class="pb-2"
            style="cursor: pointer; border-bottom: 1px dashed #979ba5">
            {{ ticketDetails.details.resource_spec.backend_group.spec_name }}（{{
              `${ticketDetails.details.resource_spec.backend_group.count} ${t('组')}`
            }}）
          </span>
        </SpecDetailPopover>
      </InfoItem>
      <InfoItem :label="t('后端存储资源标签')">
        <template v-if="ticketDetails.details.resource_spec.backend_group.label_names?.length">
          <DbTag
            v-for="item in ticketDetails.details.resource_spec.backend_group.label_names"
            :key="item">
            {{ item }}
          </DbTag>
        </template>
        <DbTag
          v-else
          theme="success">
          {{ t('通用无标签') }}
        </DbTag>
      </InfoItem>
    </template>
    <InfoItem
      :label="t('域名设置')"
      style="flex: 1 0 100%">
      <TicketInfoTable
        :data="ticketDetails.details.domains"
        row-key="key">
        <TicketInfoTableColumn
          col-key="master"
          fixed="left"
          :get-copy-value="(row: Props['ticketDetails']['details']['domains'][number]) => row.master"
          :min-width="240"
          :title="t('主访问入口')" />
        <TicketInfoTableColumn
          col-key="slave"
          :get-copy-value="(row: Props['ticketDetails']['details']['domains'][number]) => row.slave"
          :min-width="240"
          :title="t('从访问入口')" />
        <TicketInfoTableColumn
          col-key="deployStructure"
          :min-width="120"
          :title="t('部署架构')">
          {{ clusterTypeInfos[ClusterTypes.TENDBHA].name }}
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="version"
          :min-width="120"
          :title="t('数据库版本')">
          {{ ticketDetails.details.db_version }}
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="charset"
          :min-width="120"
          :title="t('字符集')">
          {{ ticketDetails.details.charset }}
        </TicketInfoTableColumn>
      </TicketInfoTable>
    </InfoItem>
  </InfoList>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { clusterTypeInfos, ClusterTypes, TicketTypes } from '@common/const';

  import SpecDetailPopover from '@components/spec-detail-popover/Index.vue';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';
  import RegionRequirements from '../components/RegionRequirements.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.HaApply>;
  }

  defineOptions({
    name: TicketTypes.MYSQL_HA_APPLY,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
<style lang="less" scoped>
  .info-title {
    font-weight: bold;
  }
</style>
