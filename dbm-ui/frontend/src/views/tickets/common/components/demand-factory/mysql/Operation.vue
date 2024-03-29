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
  <div
    v-if="isAddAuthorization"
    class="ticket-details__info">
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('访问源') }}：</span>
        <span class="ticket-details__item-value">
          <a
            href="javascript:"
            @click="handleAccessSource">
            <strong>{{ authorizeData?.source_ips.length }}</strong>
            <span style="color: #63656e">{{ $t('台') }}</span>
          </a>
        </span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('目标集群') }}：</span>
        <span class="ticket-details__item-value">
          <a
            href="javascript:"
            @click="handleTargetCluster">
            <strong>{{ authorizeData?.target_instances.length }}</strong>
            <span style="color: #63656e">{{ $t('个') }}（{{ clusterType }}）</span>
          </a>
        </span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('账号名') }}：</span>
        <span class="ticket-details__item-value">{{ authorizeData?.user || '--' }}</span>
      </div>
      <div
        class="ticket-details__item"
        style="overflow: visible">
        <span class="ticket-details__item-label">{{ $t('访问DB') }}：</span>
        <span>
          <BkTag
            v-for="(item, index) in authorizeData?.access_dbs || []"
            :key="index">
            {{ item }}
          </BkTag>
        </span>
      </div>
    </div>
    <div class="mysql-table">
      <span>{{ $t('权限明细') }}：</span>
      <DbOriginalTable
        :columns="columns"
        :data="state.accessData"
        style="width: 800px" />
    </div>
  </div>
  <div
    v-else
    class="ticket-details__info">
    <div class="ticket-details__list">
      <span>{{ $t('Excel文件') }}：</span>
      <div>
        <i class="db-icon-excel" />
        <a :href="excelUrl">{{ $t('批量授权文件') }} <i class="db-icon-import" /></a>
      </div>
    </div>
  </div>
  <HostPreview
    v-model:is-show="previewAccessSource.isShow"
    :fetch-nodes="getHostInAuthorize"
    :fetch-params="fetchNodesParams"
    :title="previewAccessSource.title" />
  <TargetClusterPreview
    v-model:is-show="previewTargetCluster.isShow"
    :ticket-details="props.ticketDetails"
    :title="previewTargetCluster.title" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { queryAccountRules } from '@services/permission';
  import { getHostInAuthorize } from '@services/ticket';
  import type {
    MysqlAuthorizationDetails,
    TicketDetails,
  } from '@services/types/ticket';

  import {
    ClusterTypes,
    TicketTypes,
  } from '@common/const';

  import HostPreview from '@components/host-preview/HostPreview.vue';

  import TargetClusterPreview from './TargetClusterPreview.vue';

  type AccessDetails = {
    access_db: string,
    account_id: number,
    bk_biz_id: number
    create_time: string,
    creator: string,
    privilege: string,
    rule_id: number,
  }

  interface Props {
    ticketDetails: TicketDetails<MysqlAuthorizationDetails>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const state = reactive({
    accessData: [] as AccessDetails[],
  });

  const columns = [{
    label: 'DB',
    field: 'access_db',
  }, {
    label: t('权限'),
    field: 'privilege',
    showOverflowTooltip: true,
    render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
  }];

  /**
   * 是否是添加授权
   */
  const isAddAuthorization = computed(() => props.ticketDetails?.ticket_type === TicketTypes.MYSQL_AUTHORIZE_RULES);

  /**
   * 区分集群类型
   */
  const clusterType = computed(() => {
    if (props.ticketDetails?.details?.authorize_data?.cluster_type === ClusterTypes.TENDBHA) {
      return t('主从');
    }
    return t('单节点');
  });

  const authorizeData = computed(() => props.ticketDetails?.details?.authorize_data);

  const excelUrl = computed(() => props.ticketDetails?.details.excel_url);

  const fetchNodesParams = computed(() => ({
    bk_biz_id: props.ticketDetails.bk_biz_id,
    ticket_id: props.ticketDetails.id,
  }));

  watch(() => props.ticketDetails.ticket_type, (data) => {
    if (data === TicketTypes.MYSQL_AUTHORIZE_RULES) {
      const {
        bk_biz_id: bizId,
        details,
      } = props.ticketDetails;
      const params = {
        bizId,
        user: details?.authorize_data?.user,
        access_dbs: details?.authorize_data?.access_dbs,
      };
      queryAccountRules(params)
        .then((res) => {
          state.accessData = res.results[0]?.rules;
        })
        .catch(() => {
          state.accessData = [];
        });
    }
  }, { immediate: true, deep: true });

  const previewAccessSource = reactive({
    isShow: false,
    title: t('访问源预览'),
  });

  const previewTargetCluster = reactive({
    isShow: false,
    title: t('目标集群预览'),
  });

  function handleAccessSource() {
    previewAccessSource.isShow = true;
  }

  function handleTargetCluster() {
    previewTargetCluster.isShow = true;
  }
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/ticketDetails.less';

  .mysql-table {
    display: flex;

    span {
      display: inline;
      width: 160px;
      text-align: right;
    }
  }

  .db-icon-excel {
    margin-right: 5px;
    color: #2dcb56;
  }
</style>
