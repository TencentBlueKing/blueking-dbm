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
  <InfoList>
    <InfoItem :label="t('角色类型')">
      {{ nodeType === NodeType.PROXY ? t('接入层') : t('存储层') }}
    </InfoItem>
    <InfoItem :label="t('升级类型')">
      {{ updateType === UpdateType.CLUSTER ? t('指定集群升级') : t('指定主机升级') }}
    </InfoItem>
  </InfoList>
  <component
    :is="currentTable"
    :ticket-details="ticketDetails" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  import BackendCluster from './components/BackendCluster.vue';
  import BackendMachine from './components/BackendMachine.vue';
  import ProxyCluster from './components/ProxyCluster.vue';
  import ProxyMachine from './components/ProxyMachine.vue';

  interface Props {
    ticketDetails: TicketModel<Redis.VersionUpdateOnline>;
  }

  defineOptions({
    name: TicketTypes.REDIS_VERSION_UPDATE_ONLINE,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const NodeType = {
    BACKEND: 'Backend',
    PROXY: 'Proxy',
  };

  const UpdateType = {
    CLUSTER: 'cluster',
    MACHINE: 'machine',
  };

  const { infos, update_type: updateType } = props.ticketDetails.details;
  const nodeType = infos[0].node_type;

  const currentTable = computed(() => {
    const key = `${nodeType}_${updateType}`;
    const componentMap = {
      [`${NodeType.BACKEND}_${UpdateType.CLUSTER}`]: BackendCluster,
      [`${NodeType.BACKEND}_${UpdateType.MACHINE}`]: BackendMachine,
      [`${NodeType.PROXY}_${UpdateType.CLUSTER}`]: ProxyCluster,
      [`${NodeType.PROXY}_${UpdateType.MACHINE}`]: ProxyMachine,
    };
    return componentMap[key];
  });
</script>
