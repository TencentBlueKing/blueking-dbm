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
    <InfoItem :label="t('替换类型')">
      {{ operaObjectMap[ticketDetails.details.opera_object].title }}
    </InfoItem>
    <InfoItem :label="t('主机选择方式')">
      {{ ticketDetails.details.source_type === SourceType.RESOURCE_AUTO ? t('资源池自动匹配') : t('资源池手动选择') }}
    </InfoItem>
  </InfoList>
  <Component
    :is="operaObjectMap[ticketDetails.details.opera_object].table"
    v-bind="props" />
  <InfoList>
    <InfoItem :label="t('检查业务连接')">
      {{ ticketDetails.details.force ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';
  import { OperaObejctType, SourceType } from '@services/types';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../../../components/info-list/Index.vue';

  import InstanceReplace from './components/InstanceReplace.vue';
  import MachineReplace from './components/MachineReplace.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.ResourcePool.ProxySwitch>;
  }

  defineOptions({
    name: TicketTypes.MYSQL_PROXY_SWITCH,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const operaObjectMap = {
    [OperaObejctType.INSTANCE]: {
      table: InstanceReplace,
      title: t('实例替换'),
    },
    [OperaObejctType.MACHINE]: {
      table: MachineReplace,
      title: t('整机替换'),
    },
  };
</script>
