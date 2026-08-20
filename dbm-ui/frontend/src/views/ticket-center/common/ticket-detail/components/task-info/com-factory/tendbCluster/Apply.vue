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
  <div class="ticket-details-info-title">{{ t('基本信息') }}</div>
  <InfoList>
    <InfoItem :label="t('所属业务')">
      {{ ticketDetails?.bk_biz_name || '--' }}
    </InfoItem>
    <InfoItem :label="t('业务代号')">
      {{ ticketDetails?.db_app_abbr || '--' }}
    </InfoItem>
    <InfoItem :label="t('集群名称')">
      {{ ticketDetails.details.cluster_name || '--' }}
    </InfoItem>
    <InfoItem :label="t('集群别名')">
      {{ ticketDetails.details.cluster_alias || '--' }}
    </InfoItem>
  </InfoList>
  <RegionRequirements :details="ticketDetails.details" />
  <div
    class="ticket-details-info-title"
    style="margin-top: 20px">
    {{ t('部署需求') }}
  </div>
  <InfoList>
    <InfoItem :label="t('DB模块')">
      {{ ticketDetails.details.db_module_name || '--' }}
    </InfoItem>
    <InfoItem :label="t('MySQL版本')">
      {{ ticketDetails.details.version.db_version || '--' }}
    </InfoItem>
    <InfoItem :label="t('Spider版本')">
      {{ ticketDetails.details.version.spider_version || '--' }}
    </InfoItem>
    <InfoItem :label="t('访问端口')">
      {{ ticketDetails.details.spider_port || '--' }}
    </InfoItem>
    <InfoItem :label="t('Spider Master 规格')">
      <SpecDetailPopover
        :data="ticketDetails.details.resource_spec.spider"
        placement="top">
        <span
          class="pb-2"
          style="cursor: pointer; border-bottom: 1px dashed #979ba5">
          {{ ticketDetails.details.resource_spec.spider.spec_name }}（{{
            `${ticketDetails.details.resource_spec.spider.count} ${t('台')}`
          }}）
        </span>
      </SpecDetailPopover>
    </InfoItem>
    <InfoItem :label="t('Spider Master 资源标签')">
      <template v-if="ticketDetails.details.resource_spec.spider.label_names?.length">
        <DbTag
          v-for="item in ticketDetails.details.resource_spec.spider.label_names"
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
    <InfoItem
      :label="t('后端存储')"
      style="flex: 1 0 100%">
      <TicketInfoTable
        :data="[ticketDetails.details.resource_spec.backend_group.spec_info]"
        row-key="spec_name">
        <TicketInfoTableColumn
          col-key="spec_name"
          :title="t('资源规格')">
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="label_names"
          :min-width="200"
          :title="t('资源标签')">
          <template #default>
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
          </template>
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="machine_pair"
          :title="t('需机器组数')">
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="cluster_shard_num"
          :title="t('集群分片')">
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="qps"
          :title="t('集群QPS每秒')">
          <template #default="{ row }: { row: ClusterSpecModel }">
            {{ row.qps.min * row.machine_pair || '--' }}
          </template>
        </TicketInfoTableColumn>
      </TicketInfoTable>
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import ClusterSpecModel from '@services/model/resource-spec/cluster-sepc';
  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import SpecDetailPopover from '@components/spec-detail-popover/Index.vue';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';
  import RegionRequirements from '../components/RegionRequirements.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.Apply>;
  }

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_APPLY,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
<style lang="less">
  .ticket-details-info-title {
    font-weight: bold;
  }
</style>
