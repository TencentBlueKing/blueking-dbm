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
  <strong class="ticket-details-info-title">{{ $t('业务信息') }}</strong>
  <div class="ticket-details-list">
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ $t('所属业务') }}：</span>
      <span class="ticket-details-item-value">{{ ticketDetails?.bk_biz_name || '--' }}</span>
    </div>
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ $t('业务英文名') }}：</span>
      <span class="ticket-details-item-value">{{ ticketDetails?.db_app_abbr || '--' }}</span>
    </div>
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ $t('集群名称') }}：</span>
      <span class="ticket-details-item-value">{{ ticketDetails?.details?.cluster_name || '--' }}</span>
    </div>
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ $t('集群别名') }}：</span>
      <span class="ticket-details-item-value">{{ ticketDetails?.details?.cluster_alias || '--' }}</span>
    </div>
  </div>
  <strong class="ticket-details-info-title">{{ $t('地域要求') }}</strong>
  <div class="ticket-details-list">
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ $t('数据库部署地域') }}：</span>
      <span class="ticket-details-item-value">{{ cityName }}</span>
    </div>
  </div>
  <strong class="ticket-details-info-title">{{ $t('数据库部署信息') }}</strong>
  <div class="ticket-details-list">
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ $t('容灾要求') }}：</span>
      <span class="ticket-details-item-value">{{ affinity }}</span>
    </div>
  </div>
  <strong class="ticket-details-info-title">{{ $t('部署需求') }}</strong>
  <div class="ticket-details-list">
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ $t('版本') }}：</span>
      <span class="ticket-details-item-value">{{ ticketDetails?.details?.db_version || '--' }}</span>
    </div>
    <template v-if="ticketDetails?.details?.ip_source === redisIpSources.manual_input.id">
      <div class="ticket-details-item">
        <span class="ticket-details-item-label">{{ $t('Broker节点IP') }}：</span>
        <span class="ticket-details-item-value">
          <span
            v-if="getServiceNums('broker') > 0"
            class="host-nums"
            @click="handleShowPreview('broker')">
            <a href="javascript:">{{ getServiceNums('broker') }}</a>
            {{ $t('台') }}
          </span>
          <template v-else>--</template>
        </span>
      </div>
      <div class="ticket-details-item">
        <span class="ticket-details-item-label">{{ $t('Zookeeper节点IP') }}：</span>
        <span class="ticket-details-item-value">
          <span
            v-if="getServiceNums('zookeeper') > 0"
            class="host-nums"
            @click="handleShowPreview('zookeeper')">
            <a href="javascript:">{{ getServiceNums('zookeeper') }}</a>
            {{ $t('台') }}
          </span>
          <template v-else>--</template>
        </span>
      </div>
    </template>
    <template v-else>
      <div class="ticket-details-item">
        <span class="ticket-details-item-label">{{ $t('Broker节点规格') }}：</span>
        <span class="ticket-details-item-value">
          <BkPopover
            placement="top"
            theme="light">
            <span
              class="pb-2"
              style="cursor: pointer; border-bottom: 1px dashed #979ba5">
              {{ brokerSpec?.spec_name }}（{{ `${brokerSpec?.count} ${$t('台')}` }}）
            </span>
            <template #content>
              <SpecInfos :data="brokerSpec" />
            </template>
          </BkPopover>
        </span>
      </div>
      <div class="ticket-details-item">
        <span class="ticket-details-item-label">{{ $t('Zookeeper节点规格') }}：</span>
        <span class="ticket-details-item-value">
          <BkPopover
            placement="top"
            theme="light">
            <span
              class="pb-2"
              style="cursor: pointer; border-bottom: 1px dashed #979ba5">
              {{ zookeeperSpec?.spec_name }}（{{ `${zookeeperSpec?.count} ${$t('台')}` }}）
            </span>
            <template #content>
              <SpecInfos :data="zookeeperSpec" />
            </template>
          </BkPopover>
        </span>
      </div>
    </template>
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ $t('开启认证') }}：</span>
      <span
        v-overflow-tips
        class="ticket-details-item-value">
        {{ security }}
      </span>
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
  import { useRequest } from 'vue-request';

  import TicketModel, { type Kafka } from '@services/model/ticket/ticket';
  import { getInfrasCities, getTicketHostNodes } from '@services/source/ticket';

  import { useSystemEnviron } from '@stores';

  import { TicketTypes } from '@common/const';

  import HostPreview from '@components/host-preview/HostPreview.vue';

  import { redisIpSources } from '@views/db-manage/redis/apply/common/const';

  import { firstLetterToUpper } from '@utils';

  import SpecInfos from '../components/SpecInfos.vue';

  interface Props {
    ticketDetails: TicketModel<Kafka.Apply>;
  }

  const props = defineProps<Props>();
  defineOptions({
    name: TicketTypes.KAFKA_APPLY,
    inheritAttrs: false,
  });

  const { t } = useI18n();
  const { AFFINITY: affinityList } = useSystemEnviron().urls;

  const cityName = ref('--');

  const zookeeperSpec = computed(() => props.ticketDetails?.details?.resource_spec?.zookeeper || {});
  const brokerSpec = computed(() => props.ticketDetails?.details?.resource_spec?.broker || {});
  const security = computed(() => (props.ticketDetails?.details.no_security === 0 ? t('开启') : t('不开启')));
  const affinity = computed(() => {
    const level = props.ticketDetails?.details?.disaster_tolerance_level;
    if (level && affinityList) {
      return affinityList.find((item) => item.value === level)?.label;
    }
    return '--';
  });

  useRequest(getInfrasCities, {
    onSuccess: (cityList) => {
      const cityCode = props.ticketDetails.details.city_code;
      const name = cityList.find((item) => item.city_code === cityCode)?.city_name;
      cityName.value = name ?? '--';
    },
  });

  /**
   * 获取服务器数量
   */
  function getServiceNums(key: 'broker' | 'zookeeper') {
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

  function handleShowPreview(role: 'broker' | 'zookeeper') {
    previewState.isShow = true;
    previewState.role = role;
    previewState.title = `【${firstLetterToUpper(role)}】${t('主机预览')}`;
  }
</script>
