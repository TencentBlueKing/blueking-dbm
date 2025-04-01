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
  <div class="info-title">{{ t('部署模块') }}</div>
  <InfoList>
    <InfoItem :label="t('所属业务')">
      {{ ticketDetails.bk_biz_name || '--' }}
    </InfoItem>
    <InfoItem :label="t('业务英文名')">
      {{ ticketDetails.db_app_abbr || '--' }}
    </InfoItem>
    <InfoItem :label="t('集群名称')">
      {{ ticketDetails.details.cluster_name || '--' }}
    </InfoItem>
    <InfoItem :label="t('集群别名')">
      {{ ticketDetails.details.cluster_alias || '--' }}
    </InfoItem>
  </InfoList>
  <RegionRequirements :details="ticketDetails.details" />
  <div class="info-title mt-20">{{ t('部署需求') }}</div>
  <InfoList>
    <InfoItem :label="t('版本')">
      {{ ticketDetails.details.cluster_alias || '--' }}
    </InfoItem>
    <template v-if="isFromResourcePool">
      <InfoItem :label="t('Master节点规格')">
        <BkPopover
          v-if="masterSpec"
          placement="top"
          theme="light">
          <span
            class="pb-2"
            style="cursor: pointer; border-bottom: 1px dashed #979ba5">
            {{ masterSpec.spec_name }}（{{ `${masterSpec.count} ${t('台')}` }}）
          </span>
          <template #content>
            <SpecInfos :data="masterSpec" />
          </template>
        </BkPopover>
        <span v-else>--</span>
      </InfoItem>
      <InfoItem :label="t('Client节点规格')">
        <BkPopover
          v-if="clientSpec"
          placement="top"
          theme="light">
          <span
            class="pb-2"
            style="cursor: pointer; border-bottom: 1px dashed #979ba5">
            {{ clientSpec.spec_name }}（{{ `${clientSpec.count} ${t('台')}` }}）
          </span>
          <template #content>
            <SpecInfos :data="clientSpec" />
          </template>
        </BkPopover>
        <span v-else>--</span>
      </InfoItem>
      <InfoItem :label="t('热节点规格')">
        <BkPopover
          v-if="hotSpec"
          placement="top"
          theme="light">
          <span
            class="pb-2"
            style="cursor: pointer; border-bottom: 1px dashed #979ba5">
            {{ hotSpec.spec_name }}（{{ `${hotSpec.count} ${t('台')}` }}）
          </span>
          <template #content>
            <SpecInfos :data="hotSpec" />
          </template>
        </BkPopover>
        <span v-else>--</span>
      </InfoItem>
      <InfoItem :label="t('冷节点规格')">
        <BkPopover
          v-if="coldSpec"
          placement="top"
          theme="light">
          <span
            class="pb-2"
            style="cursor: pointer; border-bottom: 1px dashed #979ba5">
            {{ coldSpec.spec_name }}（{{ `${coldSpec.count} ${t('台')}` }}）
          </span>
          <template #content>
            <SpecInfos :data="coldSpec" />
          </template>
        </BkPopover>
        <span v-else>--</span>
      </InfoItem>
    </template>
    <template v-else>
      <InfoItem :label="t('热节点IP')">
        <BkButton
          v-if="getServiceNums('hot') > 0"
          text
          theme="primary"
          @click="handleShowPreview('hot')">
          {{ t('台') }}
        </BkButton>
        <span v-else>--</span>
      </InfoItem>
      <InfoItem :label="t('冷节点IP')">
        <BkButton
          v-if="getServiceNums('cold') > 0"
          text
          theme="primary"
          @click="handleShowPreview('cold')">
          {{ t('台') }}
        </BkButton>
        <span v-else>--</span>
      </InfoItem>
      <InfoItem :label="t('Client节点IP')">
        <BkButton
          v-if="getServiceNums('client') > 0"
          text
          theme="primary"
          @click="handleShowPreview('client')">
          {{ t('台') }}
        </BkButton>
        <span v-else>--</span>
      </InfoItem>
      <InfoItem :label="t('Master节点IP')">
        <BkButton
          v-if="getServiceNums('master') > 0"
          text
          theme="primary"
          @click="handleShowPreview('master')">
          {{ t('台') }}
        </BkButton>
        <span v-else>--</span>
      </InfoItem>
    </template>
    <InfoItem :label="t('端口号')">
      {{ ticketDetails.details.http_port || '--' }}
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

  import TicketModel, { type Es } from '@services/model/ticket/ticket';
  import { getTicketHostNodes } from '@services/source/ticket';

  import { TicketTypes } from '@common/const';

  import HostPreview from '@components/host-preview/HostPreview.vue';

  import { firstLetterToUpper } from '@utils';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';
  import RegionRequirements from '../components/RegionRequirements.vue';
  import SpecInfos from '../components/SpecInfos.vue';

  interface Props {
    ticketDetails: TicketModel<Es.Apply>;
  }

  defineOptions({
    name: TicketTypes.ES_APPLY,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isFromResourcePool = props.ticketDetails.details.ip_source === 'resource_pool';

  const { resource_spec: resourceSpec } = props.ticketDetails?.details;
  const { client: clientSpec, cold: coldSpec, hot: hotSpec, master: masterSpec } = resourceSpec;

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
    previewState.title = `【${firstLetterToUpper(role)}】${t('主机预览')}`;
  }
</script>

<style lang="less" scoped>
  .info-title {
    font-weight: bold;
    color: #313238;
  }
</style>
