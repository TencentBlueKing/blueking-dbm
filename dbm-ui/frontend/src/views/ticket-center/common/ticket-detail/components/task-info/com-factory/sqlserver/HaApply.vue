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
  <div class="info-title mt-20">{{ t('数据库部署信息') }}</div>
  <InfoList>
    <InfoItem :label="t('数据库部署地域：')">
      {{ ticketDetails.details.city_name }}
    </InfoItem>
    <InfoItem :label="t('SQLServer起始端口：')">
      {{ ticketDetails.details.start_mssql_port }}
    </InfoItem>
  </InfoList>
  <div class="info-title mt-20">{{ t('需求信息') }}</div>
  <InfoList>
    <InfoItem :label="t('集群数量：')">
      {{ ticketDetails.details.cluster_count }}
    </InfoItem>
    <InfoItem :label="t('每组主机部署集群：')">
      {{ ticketDetails.details.inst_num }}
    </InfoItem>
    <InfoItem :label="t('服务器选择：')">
      {{ ticketDetails.details.ip_source === 'resource_pool' ? t('自动从资源池匹配') : t('业务空闲机') }}
    </InfoItem>
    <InfoItem
      v-if="resourceSpecs"
      :label="t('后端存储规格：')">
      <BkPopover
        placement="top"
        theme="light">
        <span
          class="pb-2"
          style="cursor: pointer; border-bottom: 1px dashed #979ba5">
          {{ resourceSpecs.spec_name }}（{{ resourceSpecs.count }} {{ t('组') }}）
        </span>
        <template #content>
          <SpecInfos :data="resourceSpecs" />
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
          {{ t('高可用部署') }}
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
          v-if="ticketDetails.details.nodes?.sqlserver_ha"
          field="sqlserver_ha"
          :label="t('服务器')"
          :min-width="180">
          <template
            v-for="host in ticketDetails.details.nodes.sqlserver_ha"
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

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';
  import SpecInfos from '../components/SpecInfos.vue';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.HaApply>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.SQLSERVER_HA_APPLY,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const resourceSpecs = computed(() => {
    if (!props.ticketDetails.details.resource_spec) {
      return undefined;
    }
    const data = props.ticketDetails.details.resource_spec;
    // data.sqlserver_ha 历史数据兼容问题, 类型不需要定义
    // eslint-disable-next-line
    // @ts-ignore
    return data.sqlserver_ha || data.backend_group;
  });
</script>
<style lang="less" scoped>
  .info-title {
    font-weight: bold;
    color: #313238;
  }
</style>
