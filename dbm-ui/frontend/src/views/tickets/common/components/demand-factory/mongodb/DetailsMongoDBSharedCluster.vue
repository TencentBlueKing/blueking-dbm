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
  <div class="ticket-details__info">
    <strong class="ticket-details__info-title">{{ t('业务信息') }}</strong>
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('所属业务') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.bk_biz_name || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('业务英文名') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.db_app_abbr || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('集群ID') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.cluster_id || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('集群名称') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.cluster_name || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('集群别名') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.cluster_alias || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('管控区域') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.bk_cloud_name || '--' }}</span>
      </div>
    </div>
  </div>
  <div class="ticket-details__info">
    <strong class="ticket-details__info-title">{{ t('地域要求') }}</strong>
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('数据库部署地域') }}：</span>
        <span class="ticket-details__item-value">{{ cityName }}</span>
      </div>
    </div>
  </div>
  <div class="ticket-details__info">
    <strong class="ticket-details__info-title">{{ t('数据库部署信息') }}</strong>
    <div class="ticket-details__list">
      <div
        class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('容灾要求') }}：</span>
        <span class="ticket-details__item-value">{{ affinity }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('MongoDB版本') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.db_version || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('访问端口') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.start_port || '--' }}</span>
      </div>
    </div>
  </div>
  <div class="ticket-details__info">
    <strong class="ticket-details__info-title">{{ t('部署需求') }}</strong>
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('Config Server资源规格') }}：</span>
        <span class="ticket-details__item-value">
          <BkPopover
            placement="top"
            theme="light">
            <span
              class="pb-2"
              style="cursor: pointer;border-bottom: 1px dashed #979ba5;">
              {{ configServerSpec?.spec_name }}（{{ `${configServerSpec?.count} ${t('台')}` }}）
            </span>
            <template #content>
              <SpecInfos :data="configServerSpec" />
            </template>
          </BkPopover>
        </span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('Mongos资源规格') }}：</span>
        <span class="ticket-details__item-value">
          <BkPopover
            placement="top"
            theme="light">
            <span
              class="pb-2"
              style="cursor: pointer;border-bottom: 1px dashed #979ba5;">
              {{ mongosSpec?.spec_name }}（{{ `${mongosSpec?.count} ${t('台')}` }}）
            </span>
            <template #content>
              <SpecInfos :data="mongosSpec" />
            </template>
          </BkPopover>
        </span>
      </div>
      <div class="ticket-details__item whole mt-8">
        <span class="ticket-details__item-label">{{ t('ShardSvr资源规格') }}：</span>
        <span class="ticket-details__item-value">
          <BkPopover
            placement="top"
            theme="light">
            <span
              class="pb-2"
              style="cursor: pointer;border-bottom: 1px dashed #979ba5;">
              {{ ShardSvrSpec?.spec_name }}（{{ `${ShardSvrSpec?.count} ${t('台')}` }}）
            </span>
            <template #content>
              <SpecInfos :data="ShardSvrSpec" />
            </template>
          </BkPopover>
        </span>
      </div>
    </div>
    <div class="ticket-details__item">
      <span class="ticket-details__item-label">{{ t('每台主机oplog容量占比') }}：</span>
      <span class="ticket-details__item-value">{{ `${ticketDetails?.details?.oplog_percent}%` || '--' }}</span>
    </div>
  </div>
  <HostPreview
    v-model:is-show="previewState.isShow"
    :fetch-nodes="getTicketHostNodes"
    :fetch-params="fetchNodesParams"
    :title="previewState.title" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getTicketHostNodes } from '@services/source/ticket';
  import { getInfrasCities } from '@services/ticket';
  import type { TicketDetails } from '@services/types/ticket';

  import { useSystemEnviron } from '@stores';

  import HostPreview from '@components/host-preview/HostPreview.vue';

  import SpecInfos, { type SpecInfo } from '../../SpecInfos.vue';

  interface Props{
    ticketDetails: TicketDetails<{
      db_app_abbr: string,
      cap_key: string,
      city_code: string,
      city_name: string,
      cluster_id: number,
      cluster_alias: string,
      cluster_name: string,
      cluster_type: string,
      bk_cloud_name: string,
      db_version: string,
      ip_source: string,
      cap_spec: string,
      start_port: number,
      oplog_percent: number,
      proxy_port: number,
      disaster_tolerance_level: string,
      resource_spec: {
        mongo_config: SpecInfo,
        mongos: SpecInfo,
        mongodb: SpecInfo,
      },
    }>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { AFFINITY: affinityList } = useSystemEnviron().urls;

  const cityName = ref('--');

  const previewState = reactive({
    isShow: false,
    role: '',
    title: t('主机预览'),
  });

  const fetchNodesParams = computed(() => ({
    bk_biz_id: props.ticketDetails.bk_biz_id,
    id: props.ticketDetails.id,
    role: previewState.role,
  }));

  const configServerSpec = computed(() => props.ticketDetails?.details?.resource_spec?.mongo_config || {});
  const mongosSpec = computed(() => props.ticketDetails?.details?.resource_spec?.mongos || {});
  const ShardSvrSpec = computed(() => props.ticketDetails?.details?.resource_spec?.mongodb || {});

  const affinity = computed(() => {
    const level = props.ticketDetails?.details?.disaster_tolerance_level;
    if (level && affinityList) {
      return affinityList.find(item => item.value === level)?.label;
    }
    return '--';
  });

  useRequest(getInfrasCities, {
    onSuccess: (cityList) => {
      const cityCode = props.ticketDetails.details.city_code;
      const name = cityList.find(item => item.city_code === cityCode)?.city_name;
      cityName.value = name ?? '--';
    },
  });
</script>

<style lang="less" scoped>
  @import "@views/tickets/common/styles/ticketDetails.less";
</style>
