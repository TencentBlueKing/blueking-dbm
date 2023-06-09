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
        <span class="ticket-details__item-label">{{ $t('版本') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.db_version || '--' }}</span>
      </div>
      <template v-if="ticketDetails?.details?.ip_source === redisIpSources.manual_input.id">
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ $t('热节点IP') }}：</span>
          <span class="ticket-details__item-value">
            <span
              v-if="getServiceNums('hot') > 0"
              class="host-nums"
              @click="handleShowPreview('hot')">
              <a href="javascript:">{{ getServiceNums('hot') }}</a>
              {{ $t('台') }}
            </span>
            <template v-else>--</template>
          </span>
        </div>
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ $t('冷节点IP') }}：</span>
          <span class="ticket-details__item-value">
            <span
              v-if="getServiceNums('cold') > 0"
              class="host-nums"
              @click="handleShowPreview('cold')">
              <a href="javascript:">{{ getServiceNums('cold') }}</a>
              {{ $t('台') }}
            </span>
            <template v-else>--</template>
          </span>
        </div>
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ $t('Client节点IP') }}：</span>
          <span class="ticket-details__item-value">
            <span
              v-if="getServiceNums('client') > 0"
              class="host-nums"
              @click="handleShowPreview('client')">
              <a href="javascript:">{{ getServiceNums('client') }}</a>
              {{ $t('台') }}
            </span>
            <template v-else>--</template>
          </span>
        </div>
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ $t('Master节点IP') }}：</span>
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
      </template>
      <template v-else>
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ $t('Master节点规格') }}：</span>
          <span class="ticket-details__item-value">
            <BkPopover
              placement="right"
              theme="light">
              <span
                class="pb-2"
                style="border-bottom: 1px dashed #979ba5;">
                {{ masterSpec?.spec_name }}（{{ `${masterSpec?.count} ${$t('台')}` }}）
              </span>
              <template #content>
                <SpecInfos :data="masterSpec" />
              </template>
            </BkPopover>
          </span>
        </div>
        <div
          v-if="clientSpec.spec_id"
          class="ticket-details__item">
          <span class="ticket-details__item-label">{{ $t('Client节点规格') }}：</span>
          <span class="ticket-details__item-value">
            <BkPopover
              placement="right"
              theme="light">
              <span
                class="pb-2"
                style="border-bottom: 1px dashed #979ba5;">
                {{ clientSpec?.spec_name }}（{{ `${clientSpec?.count} ${$t('台')}` }}）
              </span>
              <template #content>
                <SpecInfos :data="clientSpec" />
              </template>
            </BkPopover>
          </span>
        </div>
        <div
          v-if="hotSpec.spec_id"
          class="ticket-details__item">
          <span class="ticket-details__item-label">{{ $t('热节点规格') }}：</span>
          <span class="ticket-details__item-value">
            <BkPopover
              placement="right"
              theme="light">
              <span
                class="pb-2"
                style="border-bottom: 1px dashed #979ba5;">
                {{ hotSpec?.spec_name }}（{{ `${hotSpec?.count} ${$t('台')}` }}）
              </span>
              <template #content>
                <SpecInfos :data="clientSpec" />
              </template>
            </BkPopover>
          </span>
        </div>
        <div
          v-if="coldSpec.spec_id"
          class="ticket-details__item">
          <span class="ticket-details__item-label">{{ $t('冷节点规格') }}：</span>
          <span class="ticket-details__item-value">
            <BkPopover
              placement="right"
              theme="light">
              <span
                class="pb-2"
                style="border-bottom: 1px dashed #979ba5;">
                {{ coldSpec?.spec_name }}（{{ `${coldSpec?.count} ${$t('台')}` }}）
              </span>
              <template #content>
                <SpecInfos :data="coldSpec" />
              </template>
            </BkPopover>
          </span>
        </div>
      </template>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('端口号') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.http_port || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('备注') }}：</span>
        <span
          v-overflow-tips
          class="ticket-details__item-value">{{ ticketDetails?.remark || '--' }}</span>
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
  import type { PropType } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getTicketHostNodes } from '@services/ticket';
  import type { TicketDetails, TicketDetailsES } from '@services/types/ticket';

  import HostPreview from '@components/host-preview/HostPreview.vue';

  import { redisIpSources } from '@views/redis/apply/common/const';

  import { nodeTypeText } from '../../common/utils';
  import SpecInfos, { type SpecInfo } from '../SpecInfos.vue';

  interface Details extends TicketDetailsES {
    ip_source: string,
    resource_spec: {
      master: SpecInfo,
      client: SpecInfo,
      hot: SpecInfo,
      cold: SpecInfo,
    },
  }

  interface Props{
    ticketDetails: TicketDetails<Details>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();


  const masterSpec = computed(() => props.ticketDetails?.details?.resource_spec?.master || {});
  const clientSpec = computed(() => props.ticketDetails?.details?.resource_spec?.client || {});
  const hotSpec = computed(() => props.ticketDetails?.details?.resource_spec?.hot || {});
  const coldSpec = computed(() => props.ticketDetails?.details?.resource_spec?.cold || {});

  /**
   * 获取服务器数量
   */
  function getServiceNums(key: 'hot' | 'cold' | 'master' | 'client') {
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

  function handleShowPreview(role: 'hot' | 'cold' | 'master' | 'client') {
    previewState.isShow = true;
    previewState.role = role;
    previewState.title = `【${nodeTypeText[role]}】${t('主机预览')}`;
  }
</script>

<style lang="less" scoped>
  @import "../ticketDetails.less";
</style>
