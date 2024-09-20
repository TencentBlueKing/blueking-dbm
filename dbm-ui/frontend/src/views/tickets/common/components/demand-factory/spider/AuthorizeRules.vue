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
  <div v-if="isAddAuth">
    <div class="ticket-details-list">
      <div class="ticket-details-item">
        <span class="ticket-details-item-label">{{ t('访问源') }}：</span>
        <span class="ticket-details-item-value">
          <BkButton
            text
            theme="primary"
            @click="handleAccessSource">
            <strong>{{ authorizeData?.source_ips?.length || 0 }}</strong>
          </BkButton>
          <span>{{ t('台') }}</span>
        </span>
      </div>
      <div class="ticket-details-item">
        <span class="ticket-details-item-label">{{ t('目标集群') }}：</span>
        <span class="ticket-details-item-value">
          <BkButton
            text
            theme="primary"
            @click="handleTargetCluster">
            <strong>{{ authorizeData?.target_instances.length || 0 }}</strong>
          </BkButton>
          <span>{{ t('个') }}（{{ clusterType }}）</span>
        </span>
      </div>
      <div class="ticket-details-item">
        <span class="ticket-details-item-label">{{ t('账号名') }}：</span>
        <span class="ticket-details-item-value">{{ authorizeData?.user || '--' }}</span>
      </div>
      <div class="ticket-details-item">
        <span class="ticket-details-item-label">{{ t('访问DB') }}：</span>
        <span>
          <BkTag
            v-for="(item, index) in authorizeData?.access_dbs || []"
            :key="index">
            {{ item }}
          </BkTag>
        </span>
      </div>
    </div>
    <div class="table">
      <span>{{ t('权限明细') }}：</span>
      <DbOriginalTable
        :columns="columns"
        :data="tableData" />
    </div>
  </div>
  <div v-else>
    <div class="ticket-details-list">
      <span>{{ t('Excel文件') }}：</span>
      <div class="excel-link">
        <DbIcon
          color="#2dcb56"
          svg
          type="excel" />
        <a :href="excelUrl">
          {{ t('批量授权文件') }}
          <DbIcon
            svg
            type="import" />
        </a>
      </div>
    </div>
  </div>
  <HostPreview
    v-model:is-show="previewAccessSourceShow"
    :fetch-nodes="getHostInAuthorize"
    :fetch-params="fetchNodesParams"
    :title="t('访问源预览')" />
  <TargetClusterPreview
    v-model="previewTargetClusterShow"
    :ticket-details="props.ticketDetails"
    :title="t('目标集群预览')" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type { MysqlAuthorizationDetails } from '@services/model/ticket/details/mysql';
  import TicketModel from '@services/model/ticket/ticket';
  import { queryAccountRules } from '@services/source/mysqlPermissionAccount';
  import { getHostInAuthorize } from '@services/source/ticket';

  import {
    AccountTypes,
    ClusterTypes,
    TicketTypes,
  } from '@common/const';

  import HostPreview from '@components/host-preview/HostPreview.vue';

  import TargetClusterPreview from './TargetClusterPreview.vue';

  interface IDataRow {
    access_db: string;
    privilege: string;
  }

  interface Props {
    ticketDetails: TicketModel<MysqlAuthorizationDetails>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const columns = [
    {
      label: 'DB',
      field: 'access_db',
      showOverflowTooltip: true,
    },
    {
      label: t('权限'),
      field: 'privilege',
      showOverflowTooltip: true,
      render: ({ cell }: { cell: string }) => <span>{cell.replace(/,/g, '，') || '--'}</span>,
    },
  ];

  const tableData = shallowRef<IDataRow[]>([]);

  // 是否是添加授权
  const isAddAuth = computed(() => props.ticketDetails?.ticket_type === TicketTypes.TENDBCLUSTER_AUTHORIZE_RULES);

  // 区分集群类型
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

  const {
    run: queryAccountRulesRun,
  } = useRequest(queryAccountRules, {
    manual: true,
    onSuccess: (data) => {
      tableData.value = data.results[0]?.rules.map((item) => ({
        access_db: item.access_db,
        privilege: item.privilege,
    }));
    }
  });

  watch(() => props.ticketDetails.ticket_type, (data) => {
    if (data === TicketTypes.TENDBCLUSTER_AUTHORIZE_RULES) {
      const {
        details,
      } = props.ticketDetails;
      if (details?.authorize_data?.privileges?.length) {
        tableData.value = details?.authorize_data?.privileges.map((item) => ({
          access_db: item.access_db,
          privilege: item.priv,
        }));
        return;
      }

      const params = {
        user: details?.authorize_data?.user,
        access_dbs: details?.authorize_data?.access_dbs,
        account_type: AccountTypes.TENDBCLUSTER,
      };
      queryAccountRulesRun(params);
    }
  }, { immediate: true, deep: true });

  const previewAccessSourceShow = ref(false);
  const previewTargetClusterShow = ref(false);

  const handleAccessSource = () => {
    previewAccessSourceShow.value = true;
  };

  const handleTargetCluster = () => {
    previewTargetClusterShow.value = true;
  };
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/ticketDetails.less';

  .table {
    display: flex;

    span {
      display: inline;
      min-width: 160px;
      text-align: right;
    }
  }

  .excel-link {
    display: flex;
    align-items: center;
  }
</style>
