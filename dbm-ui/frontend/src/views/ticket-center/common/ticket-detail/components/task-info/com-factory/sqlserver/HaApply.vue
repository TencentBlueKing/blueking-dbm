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
    <InfoItem :label="t('SQLServer 起始端口')">
      {{ ticketDetails.details.start_mssql_port || '--' }}
    </InfoItem>
  </InfoList>
  <div class="info-title mt-20">{{ t('需求信息') }}</div>
  <InfoList>
    <InfoItem :label="t('集群数量')">
      {{ ticketDetails.details.cluster_count }}
    </InfoItem>
    <InfoItem :label="t('每组主机部署集群')">
      {{ ticketDetails.details.inst_num }}
    </InfoItem>
    <InfoItem :label="t('服务器选择')">
      {{ ticketDetails.details.ip_source === 'resource_pool' ? t('自动从资源池匹配') : t('业务空闲机') }}
    </InfoItem>
    <template v-if="resourceSpecs">
      <InfoItem :label="t('后端存储规格')">
        <SpecDetailPopover
          :data="resourceSpecs"
          placement="top">
          <span
            class="pb-2"
            style="cursor: pointer; border-bottom: 1px dashed #979ba5">
            {{ resourceSpecs.spec_name }}（{{ resourceSpecs.count }} {{ t('组') }}）
          </span>
        </SpecDetailPopover>
      </InfoItem>
      <InfoItem :label="t('Proxy 资源标签')">
        <template v-if="resourceSpecs.label_names?.length">
          <DbTag
            v-for="item in resourceSpecs.label_names"
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
          :get-copy-value="(row: Props['ticketDetails']['details']['domains'][number]) =>row.master"
          :min-width="240"
          :title="t('主访问入口')" />
        <TicketInfoTableColumn
          col-key="deployStructure"
          :min-width="120"
          :title="t('部署架构')">
          {{ t('高可用部署') }}
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
        <TicketInfoTableColumn
          v-if="ticketDetails.details.nodes?.backend"
          col-key="sqlserver_ha"
          :min-width="180"
          title="Master / Slave IP">
          <template #default="{ rowIndex }">
            <div>
              <DbTag
                size="small"
                theme="info">
                M
              </DbTag>
              {{ ticketDetails.details.nodes.backend[rowIndex * 2].ip }}
            </div>
            <div>
              <DbTag
                size="small"
                theme="success">
                S
              </DbTag>
              {{ ticketDetails.details.nodes.backend[rowIndex * 2 + 1].ip }}
            </div>
          </template>
        </TicketInfoTableColumn>
      </TicketInfoTable>
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import SpecDetailPopover from '@components/spec-detail-popover/Index.vue';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';
  import RegionRequirements from '../components/RegionRequirements.vue';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.HaApply>;
  }

  defineOptions({
    name: TicketTypes.SQLSERVER_HA_APPLY,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

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
