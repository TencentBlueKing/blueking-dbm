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
  <BkTable
    :data="ticketDetails.details.infos"
    :show-overflow="false">
    <BkTableColumn
      :label="t('源集群')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.src_cluster].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('目标集群')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        <div v-if="data.dst_cluster_list.length > 0">
          <p
            v-for="clusterId in data.dst_cluster_list"
            :key="clusterId">
            {{ ticketDetails.details.clusters[clusterId].immute_domain }}
          </p>
        </div>
        <span v-else>{{ ticketDetails.details.clusters[data.dst_cluster].immute_domain }}</span>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('迁移 DB 名')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.db_list" />
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('忽略 DB 名')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.ignore_db_list" />
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('迁移后 DB 名')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        <div
          v-if="data.rename_infos.length"
          v-bk-tooltips="t('点击查看详情')"
          style="width: fit-content; cursor: pointer"
          @click="() => handleShowDetail(data)">
          <I18nT keypath="n项已修改">
            <span style="padding-right: 4px; font-weight: bold; color: #2dcb56">
              {{ data.rename_infos.length }}
            </span>
          </I18nT>
        </div>
        <span v-else>--</span>
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('DB 名处理')">
      {{
        ticketDetails.details.need_auto_rename ? t('迁移后源DB不再使用，自动重命名') : t('迁移后源DB继续使用，DB名不变')
      }}
    </InfoItem>
  </InfoList>
  <RenameInfos
    v-if="isShow"
    :key="renameInfos.src_cluster"
    v-model:is-show="isShow"
    :data="renameInfos"
    :domain="ticketDetails.details.clusters[renameInfos.src_cluster].immute_domain" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import TagBlock from '@components/tag-block/Index.vue';

  import InfoList, { Item as InfoItem } from '../../../components/info-list/Index.vue';

  import RenameInfos from './components/rename-infos/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.DataMigrate>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  const { t } = useI18n();

  const isShow = ref(false);
  const renameInfos = reactive<RowData>({} as RowData);

  const handleShowDetail = (rowData: RowData) => {
    Object.assign(renameInfos, rowData);
    isShow.value = true;
  };
</script>
