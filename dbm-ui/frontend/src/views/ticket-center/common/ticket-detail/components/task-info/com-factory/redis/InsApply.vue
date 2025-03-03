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
    <InfoItem :label="t('所属业务')">
      {{ ticketDetails.bk_biz_name || '--' }}
    </InfoItem>
    <InfoItem :label="t('业务英文名')">
      {{ ticketDetails.db_app_abbr || '--' }}
    </InfoItem>
  </InfoList>
  <RegionRequirements :details="ticketDetails.details" />
  <div class="info-title mt-20">{{ t('数据库部署信息') }}</div>
  <InfoList>
    <InfoItem :label="t('业务英文名')">
      {{ ticketDetails.details.append_apply ? t('已有主从所在主机追加部署') : t('全新主机部署') }}
    </InfoItem>
  </InfoList>
  <div class="info-title mt-20">{{ t('数据库部署信息') }}</div>
  <InfoList>
    <InfoItem
      v-if="!isAppend"
      :label="t('Redis 起始端口')">
      {{ ticketDetails.details.port || '--' }}
    </InfoItem>
    <InfoItem :label="t('服务器选择')">
      {{ t('自动从资源池匹配') }}
    </InfoItem>
    <InfoItem
      v-if="!isAppend"
      :label="t('后端存储规格')">
      <BkPopover
        v-if="backendSpec"
        placement="top"
        theme="light">
        <span
          class="pb-2"
          style="cursor: pointer; border-bottom: 1px dashed #979ba5">
          {{ backendSpec.spec_name }}（{{ `${backendSpec.count} ${t('台')}` }}）
        </span>
        <template #content>
          <SpecInfos :data="backendSpec" />
        </template>
      </BkPopover>
      <span v-else>--</span>
    </InfoItem>
    <EstimatedCost
      v-if="ticketDetails.details.resource_spec"
      :params="{
        db_type: DBTypes.REDIS,
        resource_spec: ticketDetails.details.resource_spec,
      }" />
    <InfoItem
      :label="t('域名设置')"
      style="width: 100%">
      <BkTable :data="tableData">
        <BkTableColumn
          field="mainDomain"
          :label="t('主域名')">
        </BkTableColumn>
        <BkTableColumn
          field="databases"
          label="Databases">
        </BkTableColumn>
        <template v-if="isAppend">
          <BkTableColumn
            field="masterIp"
            :label="t('待部署主库主机')">
          </BkTableColumn>
          <BkTableColumn
            field="slaveIp"
            :label="t('待部署从库主机')">
          </BkTableColumn>
        </template>
      </BkTable>
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { DBTypes, TicketTypes } from '@common/const';

  import EstimatedCost from '../components/EstimatedCost.vue';
  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';
  import RegionRequirements from '../components/RegionRequirements.vue';
  import SpecInfos from '../components/SpecInfos.vue';

  interface Props {
    ticketDetails: TicketModel<Redis.InsApply>;
  }

  defineOptions({
    name: TicketTypes.REDIS_INS_APPLY,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { db_app_abbr: appAbbr, details } = props.ticketDetails;
  const { append_apply: isAppend, infos, port = 0, resource_spec: resourceSpec } = details;
  const backendSpec = resourceSpec.backend_group;
  const tableData = infos.map((infoItem, index) => {
    const { cluster_name: clusterName } = infoItem;
    return {
      databases: infoItem.databases,
      mainDomain: `ins.${clusterName}.${appAbbr}.db${isAppend ? '' : `#${port + index}`}`,
      masterIp: infoItem.backend_group?.master.ip,
      slaveDomain: `ins.${clusterName}.${appAbbr}.dr#${isAppend ? '' : `#${port + index}`}`,
      slaveIp: infoItem.backend_group?.slave.ip,
    };
  });
</script>

<style lang="less" scoped>
  .info-title {
    font-weight: bold;
    color: #313238;
  }
</style>
