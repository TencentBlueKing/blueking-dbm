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
    class="single-migrate-table"
    :data="ticketDetails.details.infos"
    :show-overflow="false">
    <BkTableColumn
      v-if="isDomain"
      field="display_info.domain"
      :label="t('目标集群')">
    </BkTableColumn>
    <BkTableColumn
      v-else
      field="display_info.ip"
      :label="t('目标 Master 主机')">
    </BkTableColumn>
    <BkTableColumn
      field="old_nodes"
      :label="t('关联的主从实例')"
      min-width="400">
      <template #default="{ data }: { data: RowData }">
        <div
          v-for="(item, index) in instanceMap[data.display_info[rowKey]]"
          :key="index"
          class="host-item">
          <div class="host-tag host-tag-master">M</div>
          <div>{{ item[0] }}</div>
          ，
          <div class="host-tag host-tag-slave">S</div>
          <div>{{ item[1] }}</div>
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="resource_spec"
      :label="t('规格')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.specs[data.resource_spec.backend_group.spec_id].name }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="db_version"
      :label="t('版本')">
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Redis.MigrateSingle>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.REDIS_SINGLE_INS_MIGRATE,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const isDomain = props.ticketDetails.details.infos[0].display_info.migrate_type === 'domain';
  const rowKey = isDomain ? 'domain' : 'ip';

  const instanceMap = props.ticketDetails.details.infos.reduce<Record<string, string[][]>>((prevMap, item) => {
    const masterItem = item.old_nodes.master[0];
    const slaveItem = item.old_nodes.slave[0];
    const instanceList = [`${masterItem.ip}:${masterItem.port}`, `${slaveItem.ip}:${slaveItem.port}`];
    if (prevMap[item.display_info[rowKey]]) {
      return Object.assign({}, prevMap, {
        [item.display_info[rowKey]]: prevMap[item.display_info[rowKey]].concat(instanceList),
      });
    }
    return Object.assign({}, prevMap, {
      [item.display_info[rowKey]]: [instanceList],
    });
  }, {});
</script>

<style lang="less" scoped>
  .single-migrate-table {
    .host-item {
      display: flex;
      align-items: center;

      .host-tag {
        width: 16px;
        height: 16px;
        margin-right: 4px;
        font-size: @font-size-mini;
        font-weight: bolder;
        line-height: 16px;
        text-align: center;
      }

      .host-tag-master {
        flex-shrink: 0;
        color: @primary-color;
        background-color: #cad7eb;
      }

      .host-tag-slave {
        flex-shrink: 0;
        color: #2dcb56;
        background-color: #c8e5cd;
      }
    }
  }
</style>
