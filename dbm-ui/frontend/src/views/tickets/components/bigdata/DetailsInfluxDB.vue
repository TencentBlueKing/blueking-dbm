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
    <strong class="ticket-details__info-title">{{ $t('业务信息') }}</strong>
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('所属业务') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.bk_biz_name || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('业务英文名') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.db_app_abbr || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('分组名') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.group_name || '--' }}</span>
      </div>
    </div>
  </div>
  <div class="ticket-details__info">
    <strong class="ticket-details__info-title">{{ $t('部署需求') }}</strong>
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('版本') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.db_version || '--' }}</span>
      </div>
      <template v-if="ticketDetails?.details?.ip_source === redisIpSources.manual_input.id">
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ $t('服务器') }}：</span>
          <span class="ticket-details__item-value">
            <span
              v-if="getServiceNums() > 0"
              class="host-nums"
              @click="handleShowPreview()">
              <a href="javascript:">{{ getServiceNums() }}</a>
              {{ $t('台') }}
            </span>
            <template v-else>--</template>
          </span>
        </div>
      </template>
      <template v-if="ticketDetails?.details?.ip_source === 'resource_pool'">
        <div
          class="ticket-details__item">
          <span class="ticket-details__item-label">{{ $t('规格') }}：</span>
          <span class="ticket-details__item-value">
            <BkPopover
              placement="right"
              theme="light">
              <span
                class="pb-2"
                style="border-bottom: 1px dashed #979ba5;">
                {{ influxdbSpec?.spec_name }}（{{ `${influxdbSpec?.count} ${$t('台')}` }}）
              </span>
              <template #content>
                <SpecInfos :data="influxdbSpec" />
              </template>
            </BkPopover>
          </span>
        </div>
      </template>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('访问端口') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.port || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('备注') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.remark || '--' }}</span>
      </div>
    </div>
  </div>
  <HostPreview
    v-model:is-show="previewState.isShow"
    :fetch-nodes="getTicketHostNodes"
    :fetch-params="fetchNodesParams"
    :title="previewState.title" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getTicketHostNodes } from '@services/ticket';

  import HostPreview from '@components/host-preview/HostPreview.vue';

  import { redisIpSources } from '@views/redis/apply/common/const';

  import SpecInfos, { type SpecInfo } from '../SpecInfos.vue';

  interface TicketDetails {
    id: number,
    bk_biz_id: number,
    remark: string,
    ticket_type: string,
    bk_biz_name: string,
    db_app_abbr: string,
    details: {
      group_name: string,
      bk_cloud_id: string,
      ip_source: string,
      db_app_abbr: string,
      city_code: string,
      db_version: string,
      port: number,
      group_id: string,
      nodes: {
        influxdb: [],
      },
      resource_spec: {
        influxdb: SpecInfo,
      },
    },

  }

  interface Props {
    ticketDetails: TicketDetails
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const influxdbSpec = computed(() => props.ticketDetails?.details?.resource_spec?.influxdb || {});

  /**
   * 获取服务器数量
   */
  function getServiceNums() {
    const nodes = props.ticketDetails?.details?.nodes;
    return nodes?.influxdb?.length ?? 0;
  }

  /**
   * 服务器详情预览功能
   */
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

  function handleShowPreview() {
    previewState.isShow = true;
    previewState.role = 'influxdb';
    previewState.title = `【InfluxDB】${t('主机预览')}`;
  }
</script>

<style lang="less" scoped>
  @import "../ticketDetails.less";
</style>
