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
    <InfoItem :label="t('目标集群')">
      {{ domainList.join('，') }}
    </InfoItem>
    <InfoItem
      :label="t('权限明细')"
      style="flex: 1 0 100%">
      <BkTable
        class="sqlserver-permission-table"
        :data="ruleList"
        :show-overflow="false">
        <BkTableColumn
          field="user"
          :label="t('账号名称')"
          :width="200">
          <template #default="{ data }: { data: dataItem }">
            <div
              class="sqlserver-permission-cell"
              @click="() => handleToggleExpand(data)">
              <DbIcon
                v-if="data.rule_sets.length > 1"
                class="user-icon"
                :class="[{ 'user-icon-expand': data.isExpand }]"
                type="down-shape" />
              <div class="user-name">{{ data.username }}</div>
            </div>
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="access_db"
          :label="t('访问 DB')"
          :min-width="300">
          <template #default="{ data }: { data: dataItem }">
            <div
              v-for="(rule, ruleIndex) in getRenderList(data)"
              :key="ruleIndex"
              class="sqlserver-permission-cell">
              <BkTag>{{ rule.access_db }}</BkTag>
            </div>
          </template>
        </BkTableColumn>
      </BkTable>
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.authorizeRules>;
  }

  type dataItem = {
    isExpand: boolean;
    rule_sets: {
      access_db: string;
    }[];
    username: string;
  };

  defineOptions({
    name: TicketTypes.SQLSERVER_AUTHORIZE_RULES,
    inheritAttrs: false,
  });
  const props = defineProps<Props>();
  const { t } = useI18n();

  // 是否是添加授权
  const ruleList = (props.ticketDetails.details?.authorize_data || []).reduce(
    (prevRuleList, authorizeItem) => [
      ...prevRuleList,
      {
        isExpand: true,
        rule_sets: authorizeItem.access_dbs.map((dbItem) => ({ access_db: dbItem })),
        username: authorizeItem.user,
      },
    ],
    [] as dataItem[],
  );
  const domainList = props.ticketDetails.details.authorize_data?.[0].target_instances || [];

  const getRenderList = (data: dataItem) => (data.isExpand ? data.rule_sets : data.rule_sets.slice(0, 1));

  const handleToggleExpand = (data: dataItem) => {
    if (data.rule_sets.length <= 1) {
      return;
    }
    Object.assign(data, { isExpand: !data.isExpand });
  };
</script>

<style lang="less" scoped>
  :deep(.sqlserver-permission-cell) {
    position: relative;
    display: flex;
    height: 30px;
    padding: 0 15px;
    overflow: hidden;
    line-height: 30px;
    text-align: left;
    text-overflow: ellipsis;
    white-space: nowrap;
    border-bottom: 1px solid #dcdee5;
    align-items: center;
  }

  :deep(.sqlserver-permission-cell:last-child) {
    border-bottom: 0;
  }

  :deep(.user-icon) {
    position: absolute;
    top: 50%;
    left: 15px;
    transform: translateY(-50%) rotate(-90deg);
    transition: all 0.2s;
  }

  :deep(.user-icon-expand) {
    transform: translateY(-50%) rotate(0);
  }

  :deep(.user-name) {
    display: flex;
    height: 100%;
    padding-left: 24px;
    font-weight: bold;
    cursor: pointer;
    align-items: center;
  }

  :deep(.sqlserver-permission-table) {
    transition: all 0.5s;

    td {
      .vxe-cell {
        padding: 0 !important;
      }
    }

    td:first-child {
      .cell,
      .sqlserver-permission-cell {
        height: 100% !important;
      }
    }
  }
</style>
