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
  <BkLoading :loading="isLoading">
    <PrimaryTable
      class="permission-table"
      :data="tableData"
      row-key="user">
      <TableColumn
        col-key="user"
        :ellipsis="false"
        :title="t('账号名称')"
        :width="220">
        <template #default="{ row }:{row:IDataRow}">
          <div class="account-box">
            <DbIcon
              v-if="row.rules.length > 1"
              class="flod-flag"
              :class="{
                'is-flod': rowFlodMap[row.user],
              }"
              type="down-shape"
              @click="handleToogleExpand(row.user)" />
            {{ row.user }}
          </div>
        </template>
      </TableColumn>
      <TableColumn
        col-key="access_db"
        ellipsis
        :title="t('访问的DB名')"
        :width="300">
        <template #default="{ row }:{row:IDataRow}">
          <div
            v-for="(item, index) in rowFlodMap[row.user] ? row.rules.slice(0, 1) : row.rules"
            :key="index"
            class="inner-row">
            <BkTag>{{ item.access_db }}</BkTag>
          </div>
        </template>
      </TableColumn>
      <TableColumn
        col-key="priv"
        :show-overflow-tooltip="false"
        :title="t('权限')">
        <template #default="{ row }:{row:IDataRow}">
          <div
            v-if="row.rules.length === 0"
            class="inner-row">
            --
          </div>
          <div
            v-for="(item, index) in rowFlodMap[row.user] ? row.rules.slice(0, 1) : row.rules"
            v-else
            :key="index"
            class="inner-row cell-privilege">
            <TextOverflowLayout>
              {{ item.priv.replace(/,/g, '，') }}
            </TextOverflowLayout>
          </div>
        </template>
      </TableColumn>
    </PrimaryTable>
  </BkLoading>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type OpenareaTemplateModel from '@services/model/openarea/openareaTemplate';
  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';
  import { getPermissionRules } from '@services/source/mysqlPermissionAccount';

  import { AccountTypes, ClusterTypes } from '@common/const';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  interface IDataRow {
    rules: {
      access_db: string;
      priv: string;
    }[];
    user: string;
  }

  interface Props {
    templateDetail?: OpenareaTemplateModel;
    ticketDetails: TicketModel<Mysql.OpenArea>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const rowFlodMap = ref<Record<string, boolean>>({});
  const tableData = shallowRef<IDataRow[]>([]);

  const { loading: isLoading, run: getPermissionRulesRun } = useRequest(getPermissionRules, {
    manual: true,
    onSuccess({ results }) {
      tableData.value = results.map((item) => ({
        rules: item.rules.map((rule) => ({
          access_db: rule.access_db,
          priv: rule.privilege,
        })),
        user: item.account.user,
      }));
    },
  });

  watch(
    () => props.ticketDetails,
    () => {
      // 有权限快照返回直接渲染
      if (props.ticketDetails.details.rules_set?.[0]?.privileges?.length) {
        const rulesMemo: Record<string, boolean> = {};
        tableData.value = props.ticketDetails.details.rules_set.reduce<IDataRow[]>((acc, cur) => {
          if (!rulesMemo[cur.user]) {
            rulesMemo[cur.user] = true;
            acc.push({
              rules: cur.privileges,
              user: cur.user,
            });
          }
          return acc;
        }, []);
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.templateDetail,
    () => {
      // 无权限返回则现查
      if (props.templateDetail.related_authorize.length && tableData.value.length === 0) {
        const accountTypeMap = {
          [ClusterTypes.TENDBCLUSTER]: AccountTypes.TENDBCLUSTER,
          [ClusterTypes.TENDBHA]: AccountTypes.MYSQL,
          [ClusterTypes.TENDBSINGLE]: AccountTypes.MYSQL,
        };
        getPermissionRulesRun({
          account_type: accountTypeMap[props.templateDetail.cluster_type as keyof typeof accountTypeMap],
          bk_biz_id: props.ticketDetails.bk_biz_id,
          limit: -1,
          offset: 0,
          rule_ids: props.templateDetail.related_authorize.join(','),
        });
      }
    },
  );

  const handleToogleExpand = (user: string) => {
    rowFlodMap.value[user] = !rowFlodMap.value[user];
  };
</script>

<style lang="less" scoped>
  .permission-table {
    .account-box {
      font-weight: bold;

      .flod-flag {
        display: inline-block;
        margin-right: 4px;
        cursor: pointer;
        transition: all 0.1s;

        &.is-flod {
          transform: rotateZ(-90deg);
        }
      }
    }

    .cell-privilege {
      .vxe-cell {
        padding: 0 !important;
        margin-left: -16px;

        .inner-row {
          padding-left: 32px !important;
        }
      }
    }

    .inner-row {
      display: flex;
      height: 40px;
      align-items: center;

      & ~ .inner-row {
        border-top: 1px solid #dcdee5;
      }
    }
  }
</style>
