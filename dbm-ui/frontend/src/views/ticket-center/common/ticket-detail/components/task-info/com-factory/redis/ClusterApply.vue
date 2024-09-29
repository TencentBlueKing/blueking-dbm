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
    <div class="ticket-details-info-title">{{ t('业务信息') }}</div>
    <InfoList>
      <InfoItem :label="t('所属业务')">
        {{ ticketDetails?.bk_biz_name || '--' }}
      </InfoItem>
      <InfoItem :label="t('业务英文名')">
        {{ ticketDetails?.db_app_abbr || '--' }}
      </InfoItem>
      <InfoItem :label="t('集群名称')">
        {{ ticketDetails.details.cluster_name || '--' }}
      </InfoItem>
      <InfoItem :label="t('集群别名')">
        {{ ticketDetails.details.cluster_alias || '--' }}
      </InfoItem>
    </InfoList>
    <div class="ticket-details-info-title mt-20">{{ t('地域要求') }}</div>
    <InfoList>
      <InfoItem :label="t('数据库部署地域')">
        {{ ticketDetails?.details.city_name || '--' }}
      </InfoItem>
    </InfoList>
    <div class="ticket-details-info-title mt-20">{{ t('数据库部署信息') }}</div>
    <InfoList>
      <InfoItem :label="t('容灾要求')">
        {{ affinity }}
      </InfoItem>
    </InfoList>
    <div class="ticket-details-info-title mt-20">{{ t('部署需求') }}</div>
    <InfoList>
      <InfoItem :label="t('部署架构')">
        {{ redisClusterTypes[ticketDetails.details.cluster_type as RedisClusterTypes]?.text || '--' }}
      </InfoItem>
      <InfoItem :label="t('版本')">
        {{ ticketDetails.details.db_version || '--' }}
      </InfoItem>
      <InfoItem :label="t('服务器')">
        {{ redisIpSources[ticketDetails.details.ip_source as RedisIpSources]?.text || '--' }}
      </InfoItem>
      <InfoItem :label="t('访问端口')">
        {{ ticketDetails.details.proxy_port }}
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
        <InfoItem label="Master：">
          <span
            v-if="getServiceNums('master') > 0"
            class="host-nums"
            @click="handleShowPreview('master')">
            <a href="javascript:">{{ getServiceNums('master') }}</a>
            {{ t('台') }}
          </span>
          <template v-else>--</template>
        </InfoItem>
        <InfoItem label="Slave：">
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
        <InfoItem :label="t('Proxy存储资源规格')">
          <BkPopover
            placement="top"
            theme="light">
            <span
              class="pb-2"
              style="cursor: pointer; border-bottom: 1px dashed #979ba5">
              {{ ticketDetails.details.resource_spec.proxy.spec_name }}（{{
                `${ticketDetails.details.resource_spec.proxy.count} ${t('台')}`
              }}）
            </span>
            <template #content>
              <SpecInfos :data="ticketDetails.details.resource_spec.proxy" />
            </template>
          </BkPopover>
        </InfoItem>
        <InfoItem
          :label="t('集群部署方案')"
          style="width: 100%">
          <BkTable :data="[ticketDetails.details.resource_spec.backend_group.spec_info]">
            <BkTableColumn
              field="spec_name"
              :label="t('资源规格')" />
            <BkTableColumn
              field="machine_pair"
              :label="t('需机器组数')" />
            <BkTableColumn
              field="cluster_shard_num"
              :label="t('集群分片')" />
            <BkTableColumn
              field="cluster_capacity"
              :label="t('集群容量G')" />
            <BkTableColumn
              field="cluster_capacity"
              :label="t('集群容量G')">
              <template
                #default="{
                  data,
                }: {
                  data: Props['ticketDetails']['details']['resource_spec']['backend_group']['spec_info'];
                }">
                {{ data.qps.min * data.machine_pair || '--' }}
              </template>
            </BkTableColumn>
          </BkTable>
        </InfoItem>
      </template>
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

  import {
    type RedisClusterTypes,
    redisClusterTypes,
    type RedisIpSources,
    redisIpSources,
  } from '@views/db-manage/redis/apply/common/const';

  import { firstLetterToUpper } from '@utils';

  import { useAffinity } from '../../hooks/useAffinity';
  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';
  import SpecInfos from '../components/SpecInfos.vue';

  interface Props {
    ticketDetails: TicketModel<Redis.ClusterApply>;
  }

  const props = defineProps<Props>();
  defineOptions({
    name: TicketTypes.REDIS_CLUSTER_APPLY,
    inheritAttrs: false,
  });

  const { t } = useI18n();
  const { affinity } = useAffinity(props.ticketDetails);

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
