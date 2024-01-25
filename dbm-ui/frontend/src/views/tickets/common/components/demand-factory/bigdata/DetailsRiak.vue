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
    <strong class="ticket-details__info-title">{{ t('部署模块') }}</strong>
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
        <span class="ticket-details__item-label">{{ t('DB模块名') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.db_module_name || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('集群ID') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.cluster_name || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('集群名称') }}：</span>
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
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.city_name || '--' }}</span>
      </div>
    </div>
  </div>
  <div class="ticket-details__info">
    <strong class="ticket-details__info-title">{{ t('数据库部署信息') }}</strong>
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('Riak版本') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.db_version || '--' }}</span>
      </div>
    </div>
  </div>
  <div class="ticket-details__info">
    <strong class="ticket-details__info-title">{{ t('部署需求') }}</strong>
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('服务器选择方式') }}：</span>
        <span class="ticket-details__item-value">{{ isFromResourcePool ? t('从资源池匹配') : t('手动选择') }} </span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('备注') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.remark || '--' }}</span>
      </div>
      <template v-if="isFromResourcePool">
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ t('资源规格') }}：</span>
          <span class="ticket-details__item-value">
            <BkPopover
              placement="top"
              theme="light">
              <span
                class="pb-2"
                style="cursor: pointer;border-bottom: 1px dashed #979ba5;">
                {{ riakSpec?.spec_name }}（{{ `${riakSpec?.count} ${t('台')}` }}）
              </span>
              <template #content>
                <SpecInfos :data="riakSpec" />
              </template>
            </BkPopover>
          </span>
        </div>
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ t('节点数量') }}：</span>
          <span class="ticket-details__item-value">{{ riakSpec?.count || '--' }}</span>
        </div>
      </template>
      <template v-else>
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ t('Riak节点IP') }}：</span>
          <span class="ticket-details__item-value">
            <span
              v-if="riakNodeCount > 0"
              class="host-nums">
              <BkButton
                text
                theme="primary"
                @click="handleShowPreview">
                <strong>{{ riakNodeCount }}</strong>
              </BkButton>
              {{ t('台') }}
            </span>
            <template v-else>--</template>
          </span>
        </div>
      </template>
    </div>
    <HostPreview
      v-model:is-show="previewShow"
      :fetch-nodes="getTicketHostNodes"
      :fetch-params="fetchNodesParams"
      :title="`【${firstLetterToUpper('riak')}】${t('主机预览')}`" />
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getTicketHostNodes } from '@services/source/ticket';
  import type {
    SpecInfo,
    TicketDetails,
  } from '@services/types/ticket';

  import HostPreview from '@components/host-preview/HostPreview.vue';

  import { firstLetterToUpper } from '@utils';

  import SpecInfos from '../../SpecInfos.vue';

  interface Props{
    ticketDetails: TicketDetails<{
      db_module_name: string
      cluster_name: string
      cluster_alias: string
      bk_cloud_name: string
      city_code: string
      city_name: string
      db_version: string
      ip_source: string
      resource_spec?: {
        riak: SpecInfo
      },
      nodes?: {
        riak: {
          ip: string,
          bk_host_id: number,
          bk_cloud_id: number
        }[]
      }
    }>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isFromResourcePool = props.ticketDetails.details.ip_source === 'resource_pool';

  const previewShow = ref(false);

  const riakSpec = computed(() => props.ticketDetails?.details?.resource_spec?.riak || {} as SpecInfo);
  const riakNodeCount = computed(() => props.ticketDetails.details?.nodes?.riak.length || 0);
  const fetchNodesParams = computed(() => ({
    bk_biz_id: props.ticketDetails.bk_biz_id,
    id: props.ticketDetails.id,
    role: 'riak',
  }));

  const handleShowPreview = () => {
    previewShow.value = true;
  };
</script>

<style lang="less" scoped>
  @import "@views/tickets/common/styles/ticketDetails.less";
</style>
