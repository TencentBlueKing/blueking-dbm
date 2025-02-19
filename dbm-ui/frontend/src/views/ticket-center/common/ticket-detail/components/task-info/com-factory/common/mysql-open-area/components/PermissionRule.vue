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
    <DbOriginalTable
      class="permission-table"
      :columns="columns"
      :data="tableData" />
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

  const columns = computed(() => [
    {
      field: 'user',
      label: t('账号名称'),
      render: ({ data }: { data: IDataRow }) => (
        <div class='account-box'>
          {data.rules.length > 1 && (
            <db-icon
              class={{
                'flod-flag': true,
                'is-flod': rowFlodMap.value[data.user],
              }}
              type='down-shape'
              onClick={() => handleToogleExpand(data.user)}
            />
          )}
          {data.user}
        </div>
      ),
      showOverflowTooltip: false,
      width: 220,
    },
    {
      field: 'access_db',
      label: t('访问的DB名'),
      render: ({ data }: { data: IDataRow }) => {
        const renderRules = rowFlodMap.value[data.user] ? data.rules.slice(0, 1) : data.rules;
        return renderRules.map((item) => (
          <div class='inner-row'>
            <bk-tag>{item.access_db}</bk-tag>
          </div>
        ));
      },
      showOverflowTooltip: true,
      width: 300,
    },
    {
      field: 'priv',
      label: t('权限'),
      render: ({ data }: { data: IDataRow }) => {
        if (data.rules.length === 0) {
          return <div class='inner-row'>--</div>;
        }
        const renderRules = rowFlodMap.value[data.user] ? data.rules.slice(0, 1) : data.rules;
        return renderRules.map((item) => (
          <div class='inner-row cell-privilege'>
            <TextOverflowLayout>
              {{
                default: () => item.priv.replace(/,/g, '，'),
              }}
            </TextOverflowLayout>
          </div>
        ));
      },
      showOverflowTooltip: false,
    },
  ]);

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
