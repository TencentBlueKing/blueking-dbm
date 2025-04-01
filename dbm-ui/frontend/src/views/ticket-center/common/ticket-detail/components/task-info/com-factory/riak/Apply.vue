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
    <InfoItem :label="t('DB模块名')">
      {{ ticketDetails.details.db_module_name || '--' }}
    </InfoItem>
    <InfoItem :label="t('集群ID')">
      {{ ticketDetails.details.cluster_name || '--' }}
    </InfoItem>
    <InfoItem :label="t('集群名称')">
      {{ ticketDetails.details.cluster_alias || '--' }}
    </InfoItem>
    <InfoItem :label="t('管控区域')">
      {{ ticketDetails.details.bk_cloud_name || '--' }}
    </InfoItem>
  </InfoList>
  <RegionRequirements :details="ticketDetails.details" />
  <div class="info-title mt-20">{{ t('数据库部署信息') }}</div>
  <InfoList>
    <InfoItem :label="t('Riak版本')">
      {{ ticketDetails.details.db_version || '--' }}
    </InfoItem>
  </InfoList>
  <div class="info-title mt-20">{{ t('部署需求') }}</div>
  <InfoList>
    <InfoItem :label="t('服务器选择方式')">
      {{ isFromResourcePool ? t('从资源池匹配') : t('手动选择') }}
    </InfoItem>
    <template v-if="isFromResourcePool">
      <InfoItem :label="t('资源规格')">
        <BkPopover
          v-if="riakSpec"
          placement="top"
          theme="light">
          <span
            class="pb-2"
            style="cursor: pointer; border-bottom: 1px dashed #979ba5">
            {{ riakSpec.spec_name }}（{{ `${riakSpec.count} ${t('台')}` }}）
          </span>
          <template #content>
            <SpecInfos :data="riakSpec" />
          </template>
        </BkPopover>
        <span v-else>--</span>
      </InfoItem>
      <InfoItem :label="t('节点数量')">
        {{ riakSpec?.count || '--' }}
      </InfoItem>
    </template>
    <template v-else>
      <InfoItem :label="t('Riak节点IP')">
        <BkButton
          v-if="riakNodeCount > 0"
          text
          theme="primary"
          @click="handleShowPreview">
          {{ t('台') }}
        </BkButton>
        <span v-else>--</span>
      </InfoItem>
    </template>
  </InfoList>
  <HostPreview
    v-model:is-show="previewShow"
    :fetch-nodes="getTicketHostNodes"
    :fetch-params="fetchNodesParams"
    :title="`【${firstLetterToUpper('riak')}】${t('主机预览')}`" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Riak } from '@services/model/ticket/ticket';
  import { getTicketHostNodes } from '@services/source/ticket';

  import { TicketTypes } from '@common/const';

  import HostPreview from '@components/host-preview/HostPreview.vue';

  import { firstLetterToUpper } from '@utils';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';
  import RegionRequirements from '../components/RegionRequirements.vue';
  import SpecInfos from '../components/SpecInfos.vue';

  interface Props {
    ticketDetails: TicketModel<Riak.Apply>;
  }

  defineOptions({
    name: TicketTypes.RIAK_CLUSTER_APPLY,
    inheritAttrs: false,
  });
  const props = defineProps<Props>();
  const { t } = useI18n();

  const isFromResourcePool = props.ticketDetails.details.ip_source === 'resource_pool';

  const previewShow = ref(false);

  const riakSpec = computed(() => props.ticketDetails?.details?.resource_spec.riak);
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
  .info-title {
    font-weight: bold;
    color: #313238;
  }
</style>
