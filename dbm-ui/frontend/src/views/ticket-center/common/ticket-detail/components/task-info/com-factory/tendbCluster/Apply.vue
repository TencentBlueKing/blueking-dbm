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
  <div class="ticket-details-info-title">{{ t('业务信息') }}</div>
  <InfoList>
    <InfoItem :label="t('所属业务：')">
      {{ ticketDetails?.bk_biz_name || '--' }}
    </InfoItem>
    <InfoItem :label="t('业务英文名：')">
      {{ ticketDetails?.db_app_abbr || '--' }}
    </InfoItem>
    <InfoItem :label="t('集群名称：')">
      {{ ticketDetails.details.cluster_name || '--' }}
    </InfoItem>
    <InfoItem :label="t('集群别名：')">
      {{ ticketDetails.details.cluster_alias || '--' }}
    </InfoItem>
  </InfoList>
  <div
    class="ticket-details-info-title"
    style="margin-top: 20px">
    {{ $t('地域要求') }}
  </div>
  <InfoList>
    <InfoItem :label="t('数据库部署地域：')">
      {{ ticketDetails.details.city_name }}
    </InfoItem>
  </InfoList>
  <div
    class="ticket-details-info-title"
    style="margin-top: 20px">
    {{ $t('数据库部署信息') }}
  </div>
  <InfoList>
    <InfoItem :label="t('容灾要求：')">
      {{ affinity || '--' }}
    </InfoItem>
  </InfoList>
  <div
    class="ticket-details-info-title"
    style="margin-top: 20px">
    {{ t('部署需求') }}
  </div>
  <InfoList>
    <InfoItem :label="t('DB模块：')">
      {{ ticketDetails.details.db_module_name || '--' }}
    </InfoItem>
    <InfoItem :label="t('MySQL版本：')">
      {{ ticketDetails.details.version.db_version || '--' }}
    </InfoItem>
    <InfoItem :label="t('Spider版本：')">
      {{ ticketDetails.details.version.spider_version || '--' }}
    </InfoItem>
    <InfoItem :label="t('访问端口：')">
      {{ ticketDetails.details.spider_port || '--' }}
    </InfoItem>
    <InfoItem :label="t('接入层Master：')">
      <BkPopover
        disable-outside-click
        :offset="16"
        placement="top"
        theme="light">
        <span
          class="pb-2"
          style="cursor: pointer; border-bottom: 1px dashed #979ba5">
          {{ ticketDetails.details.resource_spec.spider.spec_name }}（{{
            `${ticketDetails.details.resource_spec.spider.count} ${t('台')}`
          }}）
        </span>
        <template #content>
          <SpecInfos :data="ticketDetails.details.resource_spec.spider" />
        </template>
      </BkPopover>
    </InfoItem>
    <InfoItem
      :label="t('集群部署方案：')"
      style="width: 100%">
      <BkTable :data="[ticketDetails.details.resource_spec.backend_group.spec_info]">
        <BkTableColumn
          field="spec_name"
          :label="t('资源规格')">
        </BkTableColumn>
        <BkTableColumn
          field="machine_pair"
          :label="t('需机器组数')">
        </BkTableColumn>
        <BkTableColumn
          field="cluster_shard_num"
          :label="t('集群分片')">
        </BkTableColumn>
        <BkTableColumn
          field="cluster_shard_num"
          :label="t('集群QPS每秒')">
          <template #default="{data}: {data: ClusterSpecModel}">
            {{ data.qps.min * data.machine_pair || '--' }}
          </template>
        </BkTableColumn>
      </BkTable>
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ClusterSpecModel from '@services/model/resource-spec/cluster-sepc';
  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';
  import { getInfrasCities } from '@services/source/infras';

  import { TicketTypes } from '@common/const';

  import { useAffinity } from '../../hooks/useAffinity';
  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';
  import SpecInfos from '../components/SpecInfos.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.Apply>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_APPLY,
    inheritAttrs: false,
  });

  const { t } = useI18n();
  const { affinity } = useAffinity(props.ticketDetails);

  const cityName = ref('--');

  useRequest(getInfrasCities, {
    onSuccess: (cityList) => {
      const cityCode = props.ticketDetails.details.city_code;
      const name = cityList.find((item) => item.city_code === cityCode)?.city_name;
      cityName.value = name ?? '--';
    },
  });
</script>
<style lang="less">
  .ticket-details-info-title {
    font-weight: bold;
  }
</style>
