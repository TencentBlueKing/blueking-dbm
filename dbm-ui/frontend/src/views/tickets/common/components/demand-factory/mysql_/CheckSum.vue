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
    <InfoItem :label="t('所属业务:')">
      {{ ticketDetails?.bk_biz_name || '--' }}
    </InfoItem>
    <InfoItem :label="t('指定执行时间:')">
      {{ utcDisplayTime(ticketDetails?.details?.timing) || '--' }}
    </InfoItem>
    <InfoItem :label="t('自动修复:')">
      {{ isRepair }}
    </InfoItem>
  </InfoList>
  <BkTable :data="ticketDetails.details.infos">
    <BkTableColumn :label="t('目标集群')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('校验主库')">
      <template #default="{ data }: { data: RowData }">
        {{ data.master.ip }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('校验从库')">
      <template #default="{ data }: { data: RowData }">
        <div
          v-for="(item, index) in data?.slaves"
          :key="index">
          <p class="pt-2 pb-2">{{ item.ip }}: {{ item.port }}</p>
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('校验DB')">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="item in data.db_patterns"
          :key="item">
          {{ item }}
        </BkTag>
        <span v-if="data.db_patterns.length < 1">--</span>
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('校验表名')">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="item in data.table_patterns"
          :key="item">
          {{ item }}
        </BkTag>
        <span v-if="data.table_patterns.length < 1">--</span>
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('忽略DB')">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="item in data.ignore_dbs"
          :key="item">
          {{ item }}
        </BkTag>
        <span v-if="data.ignore_dbs.length < 1">--</span>
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('忽略表名')">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="item in data.ignore_tables"
          :key="item">
          {{ item }}
        </BkTag>
        <span v-if="data.ignore_tables.length < 1">--</span>
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, {
    Item as InfoItem,
  } from '@views/tickets/common/components/demand-factory/components/info-list/Index.vue';

  import { utcDisplayTime } from '@utils';

  interface Props {
    ticketDetails: TicketModel<Mysql.CheckSum>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.MYSQL_CHECKSUM,
  });

  const { t } = useI18n();

  // 修复数据
  const isRepair = computed(() => (props.ticketDetails?.details?.data_repair.is_repair ? t('是') : t('否')));
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
</style>
