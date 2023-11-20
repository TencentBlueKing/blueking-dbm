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
        <span class="ticket-details__item-label">{{ t('集群名称') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.cluster_name || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('集群别名') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.cluster_alias || '--' }}</span>
      </div>
    </div>
  </div>
  <div class="ticket-details__info">
    <strong class="ticket-details__info-title">{{ $t('地域要求') }}</strong>
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('数据库部署地域') }}：</span>
        <span class="ticket-details__item-value">{{ cityName }}</span>
      </div>
    </div>
  </div>
  <div class="ticket-details__info">
    <strong class="ticket-details__info-title">{{ $t('数据库部署信息') }}</strong>
    <div class="ticket-details__list">
      <div
        class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('容灾要求') }}：</span>
        <span class="ticket-details__item-value">{{ affinity }}</span>
      </div>
    </div>
  </div>
  <div class="ticket-details__info">
    <strong class="ticket-details__info-title">{{ t('部署需求') }}</strong>
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('DB模块') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.db_module_name || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('MySQL版本') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.version?.db_version || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('Spider版本') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.version?.spider_version || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('访问端口') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.spider_port || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('备注') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.remark || '--' }}</span>
      </div>
      <div
        class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('接入层Master') }}：</span>
        <span class="ticket-details__item-value">
          <BkPopover
            disable-outside-click
            :offset="16"
            placement="top"
            theme="light">
            <span
              class="pb-2"
              style="cursor: pointer;border-bottom: 1px dashed #979ba5;">
              {{ spiderSpec?.spec_name }}（{{ `${spiderSpec?.count} ${t('台')}` }}）
            </span>
            <template #content>
              <SpecInfos :data="spiderSpec" />
            </template>
          </BkPopover>
        </span>
      </div>
      <div
        class="ticket-details__item whole mt-8">
        <span class="ticket-details__item-label">{{ t('集群部署方案') }}：</span>
        <span class="ticket-details__item-value">
          <DbOriginalTable
            class="custom-edit-table"
            :columns="columns"
            :data="backendData" />
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RedisClusterSpecModel from '@services/model/resource-spec/redis-cluster-sepc';
  import { getInfrasCities } from '@services/ticket';
  import type { TicketDetails } from '@services/types/ticket';

  import { useSystemEnviron } from '@stores';

  import SpecInfos, { type SpecInfo } from '../../SpecInfos.vue';

  interface Details {
    bk_cloud_id: number,
    db_app_abbr: string,
    cluster_name: string,
    cluster_alias: string,
    ip_source: string,
    city_code: string,
    db_module_id: number,
    spider_port: number,
    cluster_shard_num: number,
    remote_shard_num: number,
    bk_cloud_name: string,
    charset: string,
    version: {
      db_version: string,
      spider_version: string
    },
    db_module_name: string,
    city_name: string,
    machine_pair_cnt: number,
    disaster_tolerance_level: string,
    resource_spec: {
      spider: SpecInfo,
      backend_group: {
        count: number,
        spec_id: string,
        spec_info: RedisClusterSpecModel
      },
    },
  }

  interface Props{
    ticketDetails: TicketDetails<Details>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { AFFINITY: affinityList } = useSystemEnviron().urls;

  const cityName = ref('--');

  const spiderSpec = computed(() => props.ticketDetails?.details?.resource_spec?.spider || {});
  const backendData = computed(() => {
    const data = props.ticketDetails?.details?.resource_spec?.backend_group?.spec_info;
    return data ? [data] : [];
  });

  const affinity = computed(() => {
    const level = props.ticketDetails?.details?.disaster_tolerance_level;
    if (level && affinityList) {
      return affinityList.find(item => item.value === level)?.label;
    }
    return '--';
  });

  const columns = [
    {
      field: 'spec_name',
      label: t('资源规格'),
      showOverflowTooltip: true,
    },
    {
      field: 'machine_pair',
      label: t('需机器组数'),
    },
    {
      field: 'cluster_shard_num',
      label: t('集群分片'),
    },
    {
      field: 'cluster_capacity',
      label: t('集群容量G'),
    },
    {
      field: 'qps',
      label: t('集群QPS每秒'),
      render: ({ data }: {data: RedisClusterSpecModel}) => data.qps.min * data.machine_pair,
    },
  ];

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
