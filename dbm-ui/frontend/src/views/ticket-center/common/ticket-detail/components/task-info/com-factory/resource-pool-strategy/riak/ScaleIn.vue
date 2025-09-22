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
    <InfoItem :label="t('集群')">
      {{ ticketDetails.details.clusters[ticketDetails.details.cluster_id].immute_domain || '--' }}
    </InfoItem>
    <InfoItem :label="t('集群ID')">
      {{ ticketDetails.details.clusters[ticketDetails.details.cluster_id].id || '--' }}
    </InfoItem>
    <InfoItem :label="t('缩容主机：')">
      <PrimaryTable
        :data="ticketDetails.details.recycle_hosts"
        ellipsis
        row-key="ip">
        <TableColumn
          col-key="ip"
          :min-width="150"
          :title="t('节点 IP')"
          :width="250" />
        <TableColumn
          col-key="status"
          :min-width="150"
          :title="t('Agent状态')"
          :width="150">
          <template #default="{ row }">
            <RenderHostStatus :data="row.status" />
          </template>
        </TableColumn>
        <TableColumn
          col-key="bk_disk"
          :min-width="150"
          :title="t('磁盘容量(G)')"
          :width="150" />
      </PrimaryTable>
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Riak } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import RenderHostStatus from '@components/render-host-status/Index.vue';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Riak.ResourcePool.ScaleIn>;
  }

  defineOptions({
    name: TicketTypes.RIAK_CLUSTER_SCALE_IN,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
