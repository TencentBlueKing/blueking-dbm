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
  <div>
    <div class="ticket-details-info-title">{{ t('基本信息') }}</div>
    <InfoList>
      <InfoItem :label="t('所属业务')">
        {{ ticketDetails?.bk_biz_name || '--' }}
      </InfoItem>
      <InfoItem :label="t('业务代号')">
        {{ ticketDetails?.db_app_abbr || '--' }}
      </InfoItem>
      <InfoItem :label="t('集群名称')">
        {{ ticketDetails.details.cluster_name || '--' }}
      </InfoItem>
      <InfoItem :label="t('集群别名')">
        {{ ticketDetails.details.cluster_alias || '--' }}
      </InfoItem>
    </InfoList>
    <RegionRequirements :details="ticketDetails.details" />
    <div class="ticket-details-info-title mt-20">{{ t('部署配置') }}</div>
    <InfoList>
      <InfoItem :label="t('部署架构')">
        {{ redisClusterTypes[ticketDetails.details.cluster_type as RedisClusterTypes]?.text || '--' }}
      </InfoItem>
      <InfoItem :label="t('版本')">
        {{ ticketDetails.details.db_version || '--' }}
      </InfoItem>
      <InfoItem :label="t('访问端口')">
        {{ ticketDetails.details.proxy_port }}
      </InfoItem>
      <InfoItem :label="t('服务器')">
        {{ redisIpSources[ticketDetails.details.ip_source as RedisIpSources]?.text || '--' }}
      </InfoItem>
      <template v-if="ticketDetails.details.ip_source === redisIpSources.manual_input.id">
        <InfoItem :label="t('申请容量')">
          {{ getCapSpecDisplay() }}
        </InfoItem>
        <InfoItem label="Proxy：">
          <span
            v-if="getServiceNums('proxy') > 0"
            class="host-nums"
            @click="handleShowPreview('proxy')">
            <a href="javascript:">{{ getServiceNums('proxy') }}</a>
            {{ t('台') }}
          </span>
          <template v-else>--</template>
        </InfoItem>
        <InfoItem label="Master">
          <span
            v-if="getServiceNums('master') > 0"
            class="host-nums"
            @click="handleShowPreview('master')">
            <a href="javascript:">{{ getServiceNums('master') }}</a>
            {{ t('台') }}
          </span>
          <template v-else>--</template>
        </InfoItem>
        <InfoItem label="Slave">
          <span
            v-if="getServiceNums('slave') > 0"
            class="host-nums"
            @click="handleShowPreview('slave')">
            <a href="javascript:">{{ getServiceNums('slave') }}</a>
            {{ t('台') }}
          </span>
          <template v-else>--</template>
        </InfoItem>
      </template>
      <template v-else>
        <InfoItem :label="t('Proxy 规格')">
          <SpecDetailPopover
            :data="ticketDetails.details.resource_spec.proxy"
            placement="top">
            <span
              class="pb-2"
              style="cursor: pointer; border-bottom: 1px dashed #979ba5">
              {{ ticketDetails.details.resource_spec.proxy.spec_name }}（{{
                `${ticketDetails.details.resource_spec.proxy.count} ${t('台')}`
              }}）
            </span>
          </SpecDetailPopover>
        </InfoItem>
        <InfoItem :label="t('Proxy 资源标签')">
          <template v-if="ticketDetails.details.resource_spec.proxy.label_names?.length">
            <BkTag
              v-for="item in ticketDetails.details.resource_spec.proxy.label_names"
              :key="item">
              {{ item }}
            </BkTag>
          </template>
          <BkTag
            v-else
            theme="success">
            {{ t('通用无标签') }}
          </BkTag>
        </InfoItem>
        <InfoItem
          v-if="isLoadBalanceShow"
          :label="t('负载均衡')">
          {{
            [ticketDetails.details.apply_clb ? 'CLB' : '', ticketDetails.details.apply_polaris ? t('北极星') : '']
              .filter((item) => item)
              .join('，') || '--'
          }}
        </InfoItem>
        <InfoItem
          :label="t('后端存储')"
          style="flex: 1 0 100%">
          <TicketInfoTable
            :data="[ticketDetails.details.resource_spec.backend_group.spec_info]"
            row-key="spec_name">
            <TicketInfoTableColumn
              col-key="spec_name"
              :title="t('资源规格')">
              <template #default>
                <SpecDetailPopover
                  v-if="backendGroupSpec.spec_id"
                  :data="backendGroupSpec"
                  placement="top-start">
                  <span
                    class="pb-2"
                    style="cursor: pointer; border-bottom: 1px dashed #979ba5">
                    {{ backendGroupSpec.spec_name }}
                  </span>
                </SpecDetailPopover>
                <span v-else>{{ backendGroupSpec.spec_name }}</span>
              </template>
            </TicketInfoTableColumn>
            <TicketInfoTableColumn
              col-key="label_names"
              :min-width="200"
              :title="t('资源标签')">
              <template #default>
                <template v-if="ticketDetails.details.resource_spec.backend_group.label_names?.length">
                  <BkTag
                    v-for="item in ticketDetails.details.resource_spec.backend_group.label_names"
                    :key="item">
                    {{ item }}
                  </BkTag>
                </template>
                <BkTag
                  v-else
                  theme="success">
                  {{ t('通用无标签') }}
                </BkTag>
              </template>
            </TicketInfoTableColumn>
            <TicketInfoTableColumn
              col-key="machine_pair"
              :title="t('需机器组数')" />
            <TicketInfoTableColumn
              col-key="cluster_shard_num"
              :title="t('集群分片')" />
            <TicketInfoTableColumn
              col-key="cluster_capacity"
              :title="t('集群容量G')" />
          </TicketInfoTable>
        </InfoItem>
      </template>
    </InfoList>
    <div class="ticket-details-info-title">{{ t('补充信息') }}</div>
    <InfoList>
      <NotifyRelatedPersons :data="ticketDetails.config.send_msg_config" />
    </InfoList>
    <HostPreview
      v-model:is-show="previewState.isShow"
      :fetch-nodes="getTicketHostNodes"
      :fetch-params="{
        bk_biz_id: ticketDetails.bk_biz_id,
        id: ticketDetails.id,
        role: previewState.role,
      }"
      :title="previewState.title" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';
  import { getTicketHostNodes } from '@services/source/ticket';

  import { TicketTypes } from '@common/const';

  import HostPreview from '@components/host-preview/HostPreview.vue';
  import SpecDetailPopover from '@components/spec-detail-popover/Index.vue';

  import {
    type RedisClusterTypes,
    redisClusterTypes,
    type RedisIpSources,
    redisIpSources,
  } from '@views/db-manage/redis/REDIS_CLUSTER_APPLY/common/const';

  import { checkDbConsole, firstLetterToUpper } from '@utils';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';
  import NotifyRelatedPersons from '../components/NotifyRelatedPersons.vue';
  import RegionRequirements from '../components/RegionRequirements.vue';

  interface Props {
    ticketDetails: TicketModel<Redis.ClusterApply>;
  }

  defineOptions({
    name: TicketTypes.REDIS_CLUSTER_APPLY,
    inheritAttrs: false,
  });
  const props = defineProps<Props>();
  const { t } = useI18n();

  const isLoadBalanceShow = checkDbConsole('common.clb') || checkDbConsole('common.polaris');
  const backendGroupSpec = props.ticketDetails.details.resource_spec.backend_group.spec_info;

  const previewState = reactive({
    isShow: false,
    role: '',
    title: t('主机预览'),
  });

  /**
   * 获取申请容量内容
   */
  const getCapSpecDisplay = () => {
    if (!props.ticketDetails.details.cap_spec) {
      return '--';
    }

    const capSpecArr: string[] = props.ticketDetails.details.cap_spec.split(':');
    return `${capSpecArr[0]}(${(Number(capSpecArr[1]) / 1024).toFixed(2)} GB x ${capSpecArr[2]}${t('分片')})`;
  };

  /**
   * 获取服务器数量
   */
  const getServiceNums = (key: 'proxy' | 'master' | 'slave') => {
    const { nodes } = props.ticketDetails.details;
    return nodes?.[key]?.length ?? 0;
  };

  /**
   * 服务器详情预览功能
   */
  const handleShowPreview = (role: 'proxy' | 'master' | 'slave') => {
    previewState.isShow = true;
    previewState.role = role;
    previewState.title = `【${firstLetterToUpper(role)}】${t('主机预览')}`;
  };
</script>
<style lang="less" scoped>
  .ticket-details-info-title {
    font-weight: bold;
  }
</style>
