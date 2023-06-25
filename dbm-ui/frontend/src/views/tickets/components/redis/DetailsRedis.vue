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
        <span class="ticket-details__item-label">{{ $t('集群名称') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.cluster_name || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('集群别名') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.cluster_alias || '--' }}</span>
      </div>
    </div>
  </div>
  <div class="ticket-details__info">
    <strong class="ticket-details__info-title">{{ $t('部署需求') }}</strong>
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('部署架构') }}：</span>
        <span class="ticket-details__item-value">{{ getClusterType() }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('版本') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.db_version || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('服务器') }}：</span>
        <span class="ticket-details__item-value">{{ getIpSource() }}</span>
      </div>
      <template v-if="ticketDetails?.details?.ip_source === redisIpSources.manual_input.id">
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ $t('申请容量') }}：</span>
          <span class="ticket-details__item-value">{{ getCapSpecDisplay() }}</span>
        </div>
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">Proxy：</span>
          <span class="ticket-details__item-value">
            <span
              v-if="getServiceNums('proxy') > 0"
              class="host-nums"
              @click="handleShowPreview('proxy')">
              <a href="javascript:">{{ getServiceNums('proxy') }}</a>
              {{ $t('台') }}
            </span>
            <template v-else>--</template>
          </span>
        </div>
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">Master：</span>
          <span class="ticket-details__item-value">
            <span
              v-if="getServiceNums('master') > 0"
              class="host-nums"
              @click="handleShowPreview('master')">
              <a href="javascript:">{{ getServiceNums('master') }}</a>
              {{ $t('台') }}
            </span>
            <template v-else>--</template>
          </span>
        </div>
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">Slave：</span>
          <span class="ticket-details__item-value">
            <span
              v-if="getServiceNums('slave') > 0"
              class="host-nums"
              @click="handleShowPreview('slave')">
              <a href="javascript:">{{ getServiceNums('slave') }}</a>
              {{ $t('台') }}
            </span>
            <template v-else>--</template>
          </span>
        </div>
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ $t('Proxy端口') }}：</span>
          <span class="ticket-details__item-value">{{ ticketDetails?.details?.proxy_port || '--' }}</span>
        </div>
      </template>
      <template v-else>
        <div
          class="ticket-details__item">
          <span class="ticket-details__item-label">{{ $t('部署方案') }}：</span>
          <span class="ticket-details__item-value">
            {{ ticketDetails?.details?.resource_plan?.resource_plan_name }}
          </span>
        </div>
        <div
          class="ticket-details__item">
          <span class="ticket-details__item-label">{{ $t('Proxy存储资源规格') }}：</span>
          <span class="ticket-details__item-value">
            <BkPopover
              placement="right"
              theme="light">
              <span
                class="pb-2"
                style="border-bottom: 1px dashed #979ba5;">
                {{ proxySpec?.spec_name }}（{{ `${proxySpec?.count} ${$t('台')}` }}）
              </span>
              <template #content>
                <SpecInfos :data="proxySpec" />
              </template>
            </BkPopover>
          </span>
        </div>
      </template>
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
  import type { TicketDetails, TicketDetailsRedis } from '@services/types/ticket';

  import HostPreview from '@components/host-preview/HostPreview.vue';

  import {
    type RedisClusterTypes,
    redisClusterTypes,
    type RedisIpSources,
    redisIpSources,
  } from '@views/redis/apply/common/const';

  import { nodeTypeText } from '../../common/utils';
  import SpecInfos, { type SpecInfo } from '../SpecInfos.vue';

  interface Details extends TicketDetailsRedis {
    ip_source: string,
    resource_spec: {
      proxy: SpecInfo,
      backend: SpecInfo,
      single: SpecInfo,
    },
    resource_plan: {
      resource_plan_name: '',
      resource_plan_id: '',
    },
  }

  interface Props{
    ticketDetails: TicketDetails<Details>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const proxySpec = computed(() => props.ticketDetails?.details?.resource_spec?.proxy || {});

  /**
   * 获取申请容量内容
   */
  function getCapSpecDisplay() {
    if (!props.ticketDetails?.details?.cap_spec) return '--';

    const capSpecArr: string[] = props.ticketDetails?.details?.cap_spec.split(':');
    return `${capSpecArr[0]}(${(Number(capSpecArr[1]) / 1024).toFixed(2)} GB x ${capSpecArr[2]}${t('分片')})`;
  }

  /**
   * 获取部署架构类型
   */
  function getClusterType() {
    if (!props.ticketDetails?.details?.cluster_type) return '--';

    return redisClusterTypes[props.ticketDetails.details.cluster_type as RedisClusterTypes]?.text || '--';
  }

  /**
   * 获取服务器类型
   */
  function getIpSource() {
    if (!props.ticketDetails?.details?.ip_source) return '--';

    return redisIpSources[props.ticketDetails.details.ip_source as RedisIpSources]?.text || '--';
  }

  /**
   * 获取服务器数量
   */
  function getServiceNums(key: 'proxy' | 'master' | 'slave') {
    const nodes = props.ticketDetails?.details?.nodes;
    return nodes?.[key]?.length ?? 0;
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

  function handleShowPreview(role: 'proxy' | 'master' | 'slave') {
    previewState.isShow = true;
    previewState.role = role;
    previewState.title = `【${nodeTypeText[role]}】${t('主机预览')}`;
  }
</script>

<style lang="less" scoped>
  @import "../ticketDetails.less";
</style>
