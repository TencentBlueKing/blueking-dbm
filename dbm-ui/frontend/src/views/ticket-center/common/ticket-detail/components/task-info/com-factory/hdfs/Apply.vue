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
      {{ ticketDetails.details.db_version || '--' }}
    </InfoItem>
    <template v-if="isFromResourcePool">
      <InfoItem label="NameNode">
        <BkPopover
          v-if="namenodeSpec"
          placement="top"
          theme="light">
          <span
            class="pb-2"
            style="cursor: pointer; border-bottom: 1px dashed #979ba5">
            {{ namenodeSpec.spec_name }}（{{ `${namenodeSpec.count} ${t('台')}` }}）
          </span>
          <template #content>
            <SpecInfos :data="namenodeSpec" />
          </template>
        </BkPopover>
        <span v-else>--</span>
      </InfoItem>
      <InfoItem label="Zookeepers/JournalNodes">
        <BkPopover
          v-if="zookeeperSpec"
          placement="top"
          theme="light">
          <span
            class="pb-2"
            style="cursor: pointer; border-bottom: 1px dashed #979ba5">
            {{ zookeeperSpec.spec_name }}（{{ `${zookeeperSpec.count} ${t('台')}` }}）
          </span>
          <template #content>
            <SpecInfos :data="zookeeperSpec" />
          </template>
        </BkPopover>
        <span v-else>--</span>
      </InfoItem>
      <InfoItem label="DataNodes">
        <BkPopover
          v-if="datanodeSpec"
          placement="top"
          theme="light">
          <span
            class="pb-2"
            style="cursor: pointer; border-bottom: 1px dashed #979ba5">
            {{ datanodeSpec.spec_name }}（{{ `${datanodeSpec.count} ${t('台')}` }}）
          </span>
          <template #content>
            <SpecInfos :data="datanodeSpec" />
          </template>
        </BkPopover>
        <span v-else>--</span>
      </InfoItem>
    </template>
    <template v-else>
      <InfoItem :label="t('DataNode节点IP')">
        <BkButton
          v-if="getServiceNums('datanode') > 0"
          text
          theme="primary"
          @click="handleShowPreview('datanode')">
          {{ t('台') }}
        </BkButton>
        <span v-else>--</span>
      </InfoItem>
      <InfoItem :label="t('Zookeeper节点IP')">
        <BkButton
          v-if="getServiceNums('zookeeper') > 0"
          text
          theme="primary"
          @click="handleShowPreview('zookeeper')">
          {{ t('台') }}
        </BkButton>
        <span v-else>--</span>
      </InfoItem>
      <InfoItem :label="t('NameNode节点IP')">
        <BkButton
          v-if="getServiceNums('namenode') > 0"
          text
          theme="primary"
          @click="handleShowPreview('namenode')">
          {{ t('台') }}
        </BkButton>
        <span v-else>--</span>
      </InfoItem>
    </template>
    <EstimatedCost
      v-if="ticketDetails.details.resource_spec"
      :params="{
        db_type: DBTypes.HDFS,
        resource_spec: ticketDetails.details.resource_spec,
      }" />
  </InfoList>
  <HostPreview
    v-model:is-show="previewState.isShow"
    :fetch-nodes="getTicketHostNodes"
    :fetch-params="fetchNodesParams"
    :title="previewState.title" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Hdfs } from '@services/model/ticket/ticket';
  import { getTicketHostNodes } from '@services/source/ticket';

  import { DBTypes, TicketTypes } from '@common/const';

  import HostPreview from '@components/host-preview/HostPreview.vue';

  import { firstLetterToUpper } from '@utils';

  import EstimatedCost from '../components/EstimatedCost.vue';
  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';
  import RegionRequirements from '../components/RegionRequirements.vue';
  import SpecInfos from '../components/SpecInfos.vue';

  interface Props {
    ticketDetails: TicketModel<Hdfs.Apply>;
  }

  defineOptions({
    name: TicketTypes.HDFS_APPLY,
    inheritAttrs: false,
  });
  const props = defineProps<Props>();
  const { t } = useI18n();

  const isFromResourcePool = props.ticketDetails.details.ip_source === 'resource_pool';

  const zookeeperSpec = computed(() => props.ticketDetails?.details?.resource_spec?.zookeeper || {});
  const namenodeSpec = computed(() => props.ticketDetails?.details?.resource_spec?.namenode || {});
  const datanodeSpec = computed(() => props.ticketDetails?.details?.resource_spec?.datanode || {});

  /**
   * 获取服务器数量
   */
  function getServiceNums(key: 'datanode' | 'namenode' | 'zookeeper') {
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

  function handleShowPreview(role: 'datanode' | 'namenode' | 'zookeeper') {
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
