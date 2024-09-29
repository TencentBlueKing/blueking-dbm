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
  <RenderTable
    v-bind="props"
    :data="data" />
  <InfoList v-if="ticketDetails.details.excel_url">
    <InfoItem :label="t('Excel文件：')">
      <i class="db-icon-excel" />
      <a :href="ticketDetails.details.excel_url">{{ t('批量授权文件') }} <i class="db-icon-import" /></a>
    </InfoItem>
  </InfoList>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { AccountTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  import RenderTable from './components/RenderTable.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.AuthorizeRules>;
    accountType?: AccountTypes.MYSQL | AccountTypes.TENDBCLUSTER;
  }

  const props = withDefaults(defineProps<Props>(), {
    accountType: AccountTypes.MYSQL,
  });

  const { t } = useI18n();

  const data = computed(() => {
    const {
      authorize_data: authorizeData,
      authorize_data_list: authorizeDataList,
      authorize_plugin_infos: authorizePluginInfos,
    } = props.ticketDetails.details;
    // 导入授权
    if (authorizeDataList) {
      return authorizeDataList.map((item) => ({
        ips: item.source_ips as string[],
        user: item.user,
        accessDbs: item.access_dbs,
        clusterDomains: item.target_instances,
      }));
    }
    // 插件授权
    if (authorizePluginInfos) {
      return authorizePluginInfos.map((item) => ({
        ips: item.source_ips as string[],
        user: item.user,
        accessDbs: item.access_dbs,
        clusterDomains: item.target_instances,
      }));
    }
    if (authorizeData) {
      return [
        {
          ips: (authorizeData.source_ips as { ip: string }[]).map((item) => item.ip),
          user: authorizeData.user,
          accessDbs: authorizeData.access_dbs,
          clusterDomains: authorizeData.target_instances,
          privileges: authorizeData.privileges,
        },
      ];
    }
    return [];
  });
</script>

<style lang="less" scoped>
  .db-icon-excel {
    margin-right: 5px;
    color: #2dcb56;
  }
</style>
