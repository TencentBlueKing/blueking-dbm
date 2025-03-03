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
    <InfoItem :label="t('管控区域')">
      {{ ticketDetails.details.bk_cloud_name || '--' }}
    </InfoItem>
  </InfoList>
  <RegionRequirements :details="ticketDetails.details" />
  <div class="info-title mt-20">{{ t('数据库部署信息') }}</div>
  <InfoList>
    <InfoItem :label="t('MongoDB版本')">
      {{ ticketDetails.details.db_version || '--' }}
    </InfoItem>
    <InfoItem :label="t('访问端口')">
      {{ ticketDetails.details.start_port || '--' }}
    </InfoItem>
  </InfoList>
  <div class="info-title mt-20">{{ t('需求信息') }}</div>
  <InfoList>
    <InfoItem :label="t('部署副本集数量')">
      {{ ticketDetails.details.replica_count || '--' }}
    </InfoItem>
    <InfoItem :label="t('每组主机部署副本集数量')">
      {{ ticketDetails.details.node_replica_count || '--' }}
    </InfoItem>
    <InfoItem :label="t('Shard 节点数')">
      {{ ticketDetails.details.node_count || '--' }}
    </InfoItem>
    <InfoItem :label="t('规格')">
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
    <InfoItem :label="t('每台主机oplog容量占比')">
      {{ ticketDetails.details.oplog_percent || '--' }}
    </InfoItem>
    <EstimatedCost
      v-if="ticketDetails.details.resource_spec"
      :params="{
        db_type: DBTypes.MONGODB,
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
          field="clusterId"
          :label="t('集群ID')">
        </BkTableColumn>
        <BkTableColumn
          field="clusterName"
          :label="t('集群名称')">
        </BkTableColumn>
      </BkTable>
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { DBTypes, TicketTypes } from '@common/const';

  import EstimatedCost from '../components/EstimatedCost.vue';
  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';
  import RegionRequirements from '../components/RegionRequirements.vue';
  import SpecInfos from '../components/SpecInfos.vue';

  interface Props {
    ticketDetails: TicketModel<Mongodb.ReplicasetApply>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_REPLICASET_APPLY,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { replica_sets: replicaSets, resource_spec: resourceSpec } = props.ticketDetails.details;
  const backendSpec = resourceSpec.mongo_machine_set;
  const tableData = replicaSets.map((domainItem) => ({
    clusterId: domainItem.set_id,
    clusterName: domainItem.name,
    mainDomain: domainItem.domain,
  }));
</script>

<style lang="less" scoped>
  .info-title {
    font-weight: bold;
    color: #313238;
  }
</style>
