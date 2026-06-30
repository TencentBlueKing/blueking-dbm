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
  <div class="info-title">{{ t('业务信息') }}</div>
  <InfoList>
    <InfoItem :label="t('所属业务')">
      {{ ticketDetails.bk_biz_name || '--' }}
    </InfoItem>
    <InfoItem :label="t('业务 Code')">
      {{ ticketDetails.db_app_abbr || '--' }}
    </InfoItem>
    <InfoItem :label="t('集群名称')">
      {{ ticketDetails.details.cluster_name || '--' }}
    </InfoItem>
    <InfoItem :label="t('集群别名')">
      {{ ticketDetails.details.cluster_alias || '--' }}
    </InfoItem>
  </InfoList>
  <div class="info-title mt-20">{{ t('部署环境') }}</div>
  <InfoList>
    <InfoItem :label="t('部署类型')">
      {{ t('共享集群') }}
    </InfoItem>
    <InfoItem :label="t('地域')">
      {{ cityName }}
    </InfoItem>
    <InfoItem :label="t('BCS 集群')">
      {{ ticketDetails.details.k8s_cluster_name || '--' }}
    </InfoItem>
  </InfoList>
  <div class="info-title mt-20">{{ t('资源配置') }}</div>
  <InfoList>
    <InfoItem :label="t('版本')">
      {{ ticketDetails.details.db_version }}
    </InfoItem>
    <InfoItem :label="t('部署模式')">
      {{ t('集群') }}
    </InfoItem>
    <InfoItem
      label="Surreal"
      style="flex: 1 0 100%">
      <TicketInfoTable
        :data="[ticketDetails.details.component_list[0]]"
        row-key="component_name">
        <TicketInfoTableColumn
          col-key="request_cpu"
          :title="t('CPU (核)')" />
        <TicketInfoTableColumn
          col-key="request_memory"
          :title="t('内存 (GB)')">
          <template #default="{ row }: { row: { request_memory: string } }">
            {{ row.request_memory.replace('Gi', '') }}
          </template>
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="replicas"
          :title="t('节点数')" />
      </TicketInfoTable>
    </InfoItem>
    <InfoItem
      class="mt-12"
      label="TiKV"
      style="flex: 1 0 100%">
      <TicketInfoTable
        :data="[ticketDetails.details.component_list[1]]"
        row-key="component_name">
        <TicketInfoTableColumn
          col-key="request_cpu"
          :title="t('CPU (核)')" />
        <TicketInfoTableColumn
          col-key="request_memory"
          :title="t('内存 (GB)')">
          <template #default="{ row }: { row: { request_memory: string } }">
            {{ row.request_memory.replace('Gi', '') }}
          </template>
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="storage"
          :title="t('存储 (GiB)')">
          <template #default="{ row }: { row: { storage: string } }">
            {{ row.storage.replace('Gi', '') }}
          </template>
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="replicas"
          :title="t('节点数')" />
      </TicketInfoTable>
    </InfoItem>
    <InfoItem
      class="mt-12"
      label="PD"
      style="flex: 1 0 100%">
      <TicketInfoTable
        :data="[ticketDetails.details.component_list[2]]"
        row-key="component_name">
        <TicketInfoTableColumn
          col-key="request_cpu"
          :title="t('CPU (核)')" />
        <TicketInfoTableColumn
          col-key="request_memory"
          :title="t('内存 (GB)')">
          <template #default="{ row }: { row: { request_memory: string } }">
            {{ row.request_memory.replace('Gi', '') }}
          </template>
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="storage"
          :title="t('存储 (GiB)')">
          <template #default="{ row }: { row: { storage: string } }">
            {{ row.storage.replace('Gi', '') }}
          </template>
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="replicas"
          :title="t('节点数')" />
      </TicketInfoTable>
    </InfoItem>
  </InfoList>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketModel, { type SurrealDB } from '@services/model/ticket/ticket';
  import { getRegions } from '@services/source/kubernetesToolbox';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<SurrealDB.HaApply>;
  }

  defineOptions({
    name: TicketTypes.K8S_SURREALDB_HA_APPLY,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const cityName = ref('--');

  useRequest(getRegions, {
    onSuccess: (cityList) => {
      const cityCode = props.ticketDetails.details.city_code;
      const name = cityList.find((item) => item.regionCode === cityCode)?.regionName;
      cityName.value = name ?? '--';
    },
  });
</script>

<style lang="less" scoped>
  .info-title {
    font-weight: bold;
  }
</style>
