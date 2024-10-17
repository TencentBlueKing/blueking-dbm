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
    class="mysql-table">
    <DbOriginalTable
      :columns="columns"
      :data="state.accessData" />
  </div>
  <div
    v-else
    class="ticket-details-list">
    <span>{{ t('Excel文件') }}：</span>
    <div>
      <i class="db-icon-excel" />
      <a :href="excelUrl">{{ t('批量授权文件') }} <i class="db-icon-import" /></a>
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
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import type { MysqlAuthorizationDetails } from '@services/model/ticket/details/mysql';
  import TicketModel from '@services/model/ticket/ticket';
  import { queryAccountRules } from '@services/source/mysqlPermissionAccount';
  import { getHostInAuthorize } from '@services/source/ticket';

  import {
    AccountTypes,
    ClusterTypes,
    TicketTypes  } from '@common/const';

  import HostPreview from '@components/host-preview/HostPreview.vue';

  import TargetClusterPreview from './TargetClusterPreview.vue';

  export type AccessDetails = {
    access_db: string,
    account_id: number,
    bk_biz_id: number,
    create_time: string,
    creator: string,
    privilege: string,
    rule_id: number,
    source_ips: MysqlAuthorizationDetails['authorize_data']['source_ips'],
    target_instances: MysqlAuthorizationDetails['authorize_data']['target_instances'],
    user: string,
  }

  interface Props {
    ticketDetails: TicketModel<MysqlAuthorizationDetails>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const state = reactive({
    accessData: [] as AccessDetails[],
  });

  const previewAccessSource = reactive({
    isShow: false,
    title: t('访问源预览'),
  });

  const previewTargetCluster = reactive({
    isShow: false,
    title: t('目标集群预览'),
  });

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

  const isApiBatchTicket = computed(() => !!props.ticketDetails.details.authorize_plugin_infos);

  const columns = computed(() => [
    {
      label: t('账号'),
      field: 'user',
      showOverflowTooltip: true,
      width: 150,
      render: ({ data }: { data: AccessDetails }) => <span>{data.user || '--'}</span>,
    },
    {
      label: t('访问源'),
      field: 'source_ips',
      width: 120,
      render: ({ data }: { data: AccessDetails }) => (
        isApiBatchTicket.value
          ? <span>{data.source_ips.join(',')}</span>
          : <a
              href="javascript:"
              onClick={handleAccessSource}>
              <strong>{ data.source_ips.length }</strong>
              <span style="color: #63656e;">{ t('台') }</span>
            </a>
      ),
    },
    {
      label: t('目标集群'),
      field: 'target_instances',
      width: 180,
      render: ({ data }: { data: AccessDetails }) => (
        isApiBatchTicket.value
          ? <span>{data.target_instances.join(',')}</span>
          : <a
              href="javascript:"
              onClick={handleTargetCluster}>
              <strong>{ data.target_instances.length }</strong>
              <span style="color: #63656e;">{ t('个') }（{ clusterType.value }）</span>
            </a>
      ),
    },
    {
      label: t('访问DB'),
      field: 'access_db',
      render: ({ data }: { data: AccessDetails }) => <bk-tag>{ data.access_db }</bk-tag>,
    },
    {
      label: t('权限明细'),
      field: 'privilege',
      showOverflowTooltip: true,
      render: ({ data }: { data: AccessDetails }) => <span>{data.privilege || '--'}</span>,
    },
  ]);

  watch(() => props.ticketDetails.ticket_type, async (data) => {
    if (data === TicketTypes.MYSQL_AUTHORIZE_RULES) {
      if (isApiBatchTicket.value) {
        const pluginInfos = props.ticketDetails.details.authorize_plugin_infos;
        // api批量单据
        const resultList = await Promise.all(pluginInfos.map(async (info) => {
          const params = {
            bizId: info.bk_biz_id,
            user: info.user,
            access_dbs: info.access_dbs,
            account_type: AccountTypes.MYSQL,
          };
          const ruleResult = await queryAccountRules(params);

          return ruleResult.results[0].rules.map(rule => ({
            ...rule,
            source_ips: info.source_ips,
            target_instances: info.target_instances,
            user: info.user,
          }));
        }));
        state.accessData = _.flatMap(resultList);
        return;
      }
      const {
        bk_biz_id: bizId,
        details,
      } = props.ticketDetails;
      const params = {
        bizId,
        user: details?.authorize_data?.user,
        access_dbs: details?.authorize_data?.access_dbs,
        account_type: AccountTypes.MYSQL,
      };
      queryAccountRules(params)
        .then((res) => {
          state.accessData = res.results[0]?.rules.map(rule => ({
            ...rule,
            source_ips: authorizeData.value?.source_ips,
            target_instances: authorizeData.value?.target_instances,
            user: authorizeData.value?.user,
          }));
        })
        .catch(() => {
          state.accessData = [];
        });
    }
  }, {
    immediate: true,
    deep: true,
  });

  const handleAccessSource = () => {
    previewAccessSource.isShow = true;
  };

  const handleTargetCluster = () => {
    previewTargetCluster.isShow = true;
  };
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
