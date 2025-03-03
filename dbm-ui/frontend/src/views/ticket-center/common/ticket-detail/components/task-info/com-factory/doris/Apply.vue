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
  <div class="info-title mt-20">{{ t('数据库部署信息') }}</div>
  <InfoList>
    <InfoItem :label="t('Doris版本')">
      {{ ticketDetails.details.db_version || '--' }}
    </InfoItem>
    <InfoItem :label="t('服务器选择方式')">
      {{ isFromResourcePool ? t('从资源池匹配') : t('手动选择') }}
    </InfoItem>
    <InfoItem :label="t('查询端口')">
      {{ ticketDetails.details.query_port || '--' }}
    </InfoItem>
    <InfoItem :label="t('http端口')">
      {{ ticketDetails.details.http_port || '--' }}
    </InfoItem>
    <template v-if="isFromResourcePool">
      <InfoItem :label="t('Follower节点')">
        <BkPopover
          v-if="followerSpec"
          placement="top"
          theme="light">
          <span
            class="pb-2"
            style="cursor: pointer; border-bottom: 1px dashed #979ba5">
            {{ followerSpec.spec_name }}（{{ `${followerSpec.count} ${t('台')}` }}）
          </span>
          <template #content>
            <SpecInfos :data="followerSpec" />
          </template>
        </BkPopover>
        <span v-else>--</span>
      </InfoItem>
      <InfoItem :label="t('Observer节点')">
        <BkPopover
          v-if="observerSpec"
          placement="top"
          theme="light">
          <span
            class="pb-2"
            style="cursor: pointer; border-bottom: 1px dashed #979ba5">
            {{ observerSpec.spec_name }}（{{ `${observerSpec.count} ${t('台')}` }}）
          </span>
          <template #content>
            <SpecInfos :data="observerSpec" />
          </template>
        </BkPopover>
        <span v-else>--</span>
      </InfoItem>
      <InfoItem :label="t('热节点')">
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
      <InfoItem :label="t('冷节点')">
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
      <InfoItem :label="t('Follower节点IP')">
        <BkButton
          v-if="getServiceNums('follower') > 0"
          text
          theme="primary"
          @click="handleShowPreview('follower')">
          {{ t('台') }}
        </BkButton>
        <span v-else>--</span>
      </InfoItem>
      <InfoItem :label="t('Observer节点IP')">
        <BkButton
          v-if="getServiceNums('observer') > 0"
          text
          theme="primary"
          @click="handleShowPreview('observer')">
          {{ t('台') }}
        </BkButton>
        <span v-else>--</span>
      </InfoItem>
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
    </template>
    <EstimatedCost
      v-if="ticketDetails.details.resource_spec"
      :params="{
        db_type: DBTypes.DORIS,
        resource_spec: ticketDetails.details.resource_spec,
      }" />
  </InfoList>
  <HostPreview
    v-model:is-show="isPreviewShow"
    :fetch-nodes="getTicketHostNodes"
    :fetch-params="fetchNodesParams"
    :title="previewTitle" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Doris } from '@services/model/ticket/ticket';
  import { getTicketHostNodes } from '@services/source/ticket';

  import { DBTypes, TicketTypes } from '@common/const';

  import HostPreview from '@components/host-preview/HostPreview.vue';

  import { firstLetterToUpper } from '@utils';

  import EstimatedCost from '../components/EstimatedCost.vue';
  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';
  import RegionRequirements from '../components/RegionRequirements.vue';
  import SpecInfos from '../components/SpecInfos.vue';

  interface Props {
    ticketDetails: TicketModel<Doris.Apply>;
  }

  defineOptions({
    name: TicketTypes.DORIS_APPLY,
  });

  const props = defineProps<Props>();
  const { t } = useI18n();

  const isFromResourcePool = props.ticketDetails.details.ip_source === 'resource_pool';

  const { resource_spec: resourceSpec } = props.ticketDetails.details;
  const followerSpec = resourceSpec?.follower;
  const observerSpec = resourceSpec?.observer;
  const hotSpec = resourceSpec?.hot;
  const coldSpec = resourceSpec?.cold;

  const isPreviewShow = ref(false);
  const previewRole = ref('');
  const previewTitle = ref('');

  const fetchNodesParams = computed(() => ({
    bk_biz_id: props.ticketDetails.bk_biz_id,
    id: props.ticketDetails.id,
    role: previewRole.value,
  }));

  const getServiceNums = (key: 'follower' | 'observer' | 'hot' | 'cold') => {
    const nodes = props.ticketDetails.details?.nodes;
    return nodes?.[key].length ?? 0;
  };

  const handleShowPreview = (role: 'follower' | 'observer' | 'hot' | 'cold') => {
    isPreviewShow.value = true;
    previewRole.value = role;
    previewTitle.value = `【${firstLetterToUpper(role)}】${t('主机预览')}`;
  };
</script>

<style lang="less" scoped>
  .info-title {
    font-weight: bold;
    color: #313238;
  }
</style>
