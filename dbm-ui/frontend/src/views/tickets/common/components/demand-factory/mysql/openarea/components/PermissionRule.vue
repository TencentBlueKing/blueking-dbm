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
  import type { MysqlOpenAreaDetails } from '@services/model/ticket/details/mysql';
  import TicketModel from '@services/model/ticket/ticket';
  import { getPermissionRules } from '@services/source/mysqlPermissionAccount'

  import { AccountTypes, ClusterTypes } from '@common/const';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  interface IDataRow {
    user: string;
    rules: {
      priv: string;
      access_db: string;
    }[];
  }

  interface Props {
    ticketDetails: TicketModel<MysqlOpenAreaDetails>;
    templateDetail: OpenareaTemplateModel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const rowFlodMap = ref<Record<string, boolean>>({});
  const tableData = shallowRef<IDataRow[]>([]);

  const columns = computed(() => [
    {
      label: t('账号名称'),
      field: 'user',
      width: 220,
      showOverflowTooltip: false,
      render: ({ data }: { data: IDataRow }) => (
        <div class="account-box">
          {
            data.rules.length > 1
            && (
            <db-icon
              type="down-shape"
              class={{
                'flod-flag': true,
                'is-flod': rowFlodMap.value[data.user],
              }}
              onClick={() => handleToogleExpand(data.user)}/>
            )
          }
          { data.user }
        </div>
      ),
    },
    {
      label: t('访问的DB名'),
      width: 300,
      field: 'access_db',
      showOverflowTooltip: true,
      render: ({ data }: { data: IDataRow }) => {
        const renderRules = rowFlodMap.value[data.user] ? data.rules.slice(0, 1) : data.rules;
        return renderRules.map(item => (
          <div class="inner-row">
            <bk-tag>
              { item.access_db }
            </bk-tag>
          </div>
        ));
      },
    },
    {
      label: t('权限'),
      field: 'priv',
      showOverflowTooltip: false,
      render: ({ data }: { data: IDataRow }) => {
        if (data.rules.length === 0) {
          return <div class="inner-row">--</div>;
        }
        const renderRules = rowFlodMap.value[data.user] ? data.rules.slice(0, 1) : data.rules;
        return renderRules.map(item => (
          <div class="inner-row cell-privilege">
            <TextOverflowLayout>
              {{
                default: () => item.priv.replace(/,/g, '，'),
              }}
            </TextOverflowLayout>
          </div>
        ));
      },
    },
  ]);

  const { run: getPermissionRulesRun, loading: isLoading } = useRequest(getPermissionRules, {
    manual: true,
    onSuccess({ results }) {
      tableData.value = results.map((item) => ({
        user: item.account.user,
        rules: item.rules.map((rule) => ({
          priv: rule.privilege,
          access_db: rule.access_db,
        })),
      }));
    },
  });

  watch(
    () => props.ticketDetails,
    () => {
      // 有权限快照返回直接渲染
      if (props.ticketDetails.details.rules_set?.[0]?.privileges?.length) {
        const rulesMemo: Record<string, boolean> = {}
        tableData.value = props.ticketDetails.details.rules_set.reduce<IDataRow[]>((acc, cur) => {
          if (!rulesMemo[cur.user]) {
            rulesMemo[cur.user] = true;
            acc.push({
              user: cur.user,
              rules: cur.privileges,
            });
          }
          return acc;
        }, []);
      }
    },
    {
      immediate: true,
    }
  );

  watch(
    () => props.templateDetail,
    () => {
      // 无权限返回则现查
      if (props.templateDetail.related_authorize.length && tableData.value.length === 0) {
        const accountTypeMap = {
          [ClusterTypes.TENDBHA]: AccountTypes.MYSQL,
          [ClusterTypes.TENDBSINGLE]: AccountTypes.MYSQL,
          [ClusterTypes.TENDBCLUSTER]: AccountTypes.TENDBCLUSTER,
        }
        getPermissionRulesRun({
          bk_biz_id: props.ticketDetails.bk_biz_id,
          rule_ids: props.templateDetail.related_authorize.join(','),
          account_type: accountTypeMap[props.templateDetail.cluster_type as keyof typeof accountTypeMap],
          offset: 0,
          limit: -1,
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
      .cell {
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
