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
  <div class="info-title">{{ t('部署模块') }}</div>
  <InfoList>
    <InfoItem :label="t('所属业务：')">
      {{ ticketDetails.bk_biz_name || '--' }}
    </InfoItem>
    <InfoItem :label="t('业务英文名：')">
      {{ ticketDetails.db_app_abbr || '--' }}
    </InfoItem>
    <InfoItem :label="t('DB模块名：')">
      {{ ticketDetails.details.db_module_name || '--' }}
    </InfoItem>
  </InfoList>
  <div class="info-title mt-20">{{ t('地域要求') }}</div>
  <InfoList>
    <InfoItem :label="t('数据库部署地域：')">
      {{ ticketDetails.details.city_name }}
    </InfoItem>
  </InfoList>
  <div class="info-title mt-20">{{ t('数据库部署信息') }}</div>
  <InfoList>
    <InfoItem :label="t('MySQL起始端口：')">
      {{ ticketDetails?.details?.start_mysql_port || '--' }}
    </InfoItem>
  </InfoList>
  <div class="info-title mt-20">{{ t('需求信息') }}</div>
  <InfoList>
    <InfoItem
      v-if="ticketDetails.details.resource_spec?.backend"
      :label="t('后端存储资源规格：')">
      <BkPopover
        placement="top"
        theme="light">
        <span
          class="pb-2"
          style="cursor: pointer; border-bottom: 1px dashed #979ba5">
          {{ ticketDetails.details.resource_spec.backend.spec_name }}（{{
            `${ticketDetails.details.resource_spec.backend.count} ${t('台')}`
          }}）
        </span>
        <template #content>
          <SpecInfos :data="ticketDetails.details.resource_spec.backend" />
        </template>
      </BkPopover>
    </InfoItem>
    <InfoItem
      :label="t('集群设置：')"
      style="width: 100%">
      <BkTable
        :data="ticketDetails.details.domains"
        :show-overflow="false">
        <BkTableColumn
          field="master"
          fixed="left"
          :label="t('主访问入口')"
          :min-width="240" />
        <BkTableColumn
          field="deployStructure"
          :label="t('部署架构')"
          :min-width="120">
          {{ mysqlType[ticketDetails.ticket_type as MysqlTypeString].name }}
        </BkTableColumn>
        <BkTableColumn
          field="version"
          :label="t('数据库版本')"
          :min-width="120">
          {{ ticketDetails.details.db_version }}
        </BkTableColumn>
        <BkTableColumn
          field="charset"
          :label="t('字符集')"
          :min-width="120">
          {{ ticketDetails.details.charset }}
        </BkTableColumn>
        <BkTableColumn
          v-if="ticketDetails.details.nodes?.backend"
          field="backend"
          :label="t('服务器')"
          :min-width="180">
          <template
            v-for="host in ticketDetails.details.nodes.backend"
            :key="host.bk_host_id">
            <div>
              {{ host.ip }}
            </div>
          </template>
        </BkTableColumn>
      </BkTable>
    </InfoItem>
  </InfoList>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { mysqlType, type MysqlTypeString, TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';
  import SpecInfos from '../components/SpecInfos.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.SingleApply>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.MYSQL_SINGLE_APPLY,
    inheritAttrs: false,
  });

  const { t } = useI18n();
</script>
<style lang="less" scoped>
  .info-title {
    font-weight: bold;
  }
</style>
