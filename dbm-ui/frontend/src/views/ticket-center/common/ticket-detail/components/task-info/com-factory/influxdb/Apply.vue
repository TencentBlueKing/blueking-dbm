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
  <div class="info-title">{{ t('基本信息') }}</div>
  <InfoList>
    <InfoItem :label="t('所属业务')">
      {{ ticketDetails.bk_biz_name || '--' }}
    </InfoItem>
    <InfoItem :label="t('业务代号')">
      {{ ticketDetails.db_app_abbr || '--' }}
    </InfoItem>
    <InfoItem :label="t('分组名')">
      {{ ticketDetails.details.group_name || '--' }}
    </InfoItem>
  </InfoList>
  <RegionRequirements :details="ticketDetails.details" />
  <div class="info-title">{{ t('部署需求') }}</div>
  <InfoList>
    <InfoItem :label="t('版本')">
      {{ ticketDetails.details.db_version || '--' }}
    </InfoItem>
    <template v-if="isFromResourcePool">
      <InfoItem :label="t('规格')">
        <SpecDetailPopover
          v-if="influxdbSpec"
          :data="influxdbSpec"
          placement="top">
          <span
            class="pb-2"
            style="cursor: pointer; border-bottom: 1px dashed #979ba5">
            {{ influxdbSpec.spec_name }}（{{ `${influxdbSpec.count} ${t('台')}` }}）
          </span>
        </SpecDetailPopover>
        <span v-else>--</span>
      </InfoItem>
    </template>
    <template v-else>
      <InfoItem :label="t('服务器')">
        <BkButton
          v-if="getServiceNums() > 0"
          text
          theme="primary"
          @click="handleShowPreview">
          {{ t('台') }}
        </BkButton>
        <span v-else>--</span>
      </InfoItem>
    </template>
    <InfoItem :label="t('访问端口')">
      {{ ticketDetails.details.port || '--' }}
    </InfoItem>
  </InfoList>
  <HostPreview
    v-model:is-show="previewState.isShow"
    :fetch-nodes="getTicketHostNodes"
    :fetch-params="fetchNodesParams"
    :title="previewState.title" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Influxdb } from '@services/model/ticket/ticket';
  import { getTicketHostNodes } from '@services/source/ticket';

  import { TicketTypes } from '@common/const';

  import HostPreview from '@components/host-preview/HostPreview.vue';
  import SpecDetailPopover from '@components/spec-detail-popover/Index.vue';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';
  import RegionRequirements from '../components/RegionRequirements.vue';

  interface Props {
    ticketDetails: TicketModel<Influxdb.Apply>;
  }

  defineOptions({
    name: TicketTypes.INFLUXDB_APPLY,
    inheritAttrs: false,
  });
  const props = defineProps<Props>();
  const { t } = useI18n();

  const { details } = props.ticketDetails;
  const { ip_source: ipSource, nodes, resource_spec: resourceSpec } = details;

  const isFromResourcePool = ipSource === 'resource_pool';

  const influxdbSpec = resourceSpec?.influxdb;

  /**
   * 获取服务器数量
   */
  function getServiceNums() {
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
  .info-title {
    font-weight: bold;
    color: #313238;
  }
</style>
