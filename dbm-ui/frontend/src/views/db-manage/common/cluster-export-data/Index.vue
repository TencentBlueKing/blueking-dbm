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
  <DbSideslider
    v-model:is-show="isShow"
    class="export-data"
    width="960">
    <template #header>
      <span>{{ t('导出数据') }}</span>
      <div class="cluster-domain">{{ data.master_domain }}</div>
    </template>
    <Content
      :data="data"
      :ticket-type="ticketType" />
  </DbSideslider>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

  import { TicketTypes } from '@common/const';

  import Content from './component/Content.vue';

  interface Props {
    data: TendbsingleModel | TendbhaModel | TendbClusterModel;
    ticketType: TicketTypes.MYSQL_DUMP_DATA | TicketTypes.TENDBCLUSTER_DUMP_DATA;
  }

  defineProps<Props>();
  const isShow = defineModel<boolean>('isShow', {
    required: true,
    default: false,
  });

  const { t } = useI18n();
</script>

<style lang="less">
  .export-data {
    .cluster-domain {
      padding-left: 8px;
      margin-left: 8px;
      font-size: 14px;
      color: #979ba5;
      border-left: 1px solid #dcdee5;
    }
  }
</style>
