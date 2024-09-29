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

  import MysqlPermissonAccountModel from '@services/model/mysql/mysql-permission-account';
  import { getPermissionRules } from '@services/source/permission';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';


  interface Props {
    clusterType: ClusterTypes.TENDBHA | ClusterTypes.TENDBSINGLE | ClusterTypes.TENDBCLUSTER;
    ruleIds?: number[];
  }

  const props = withDefaults(defineProps<Props>(), {
    clusterType: ClusterTypes.TENDBHA,
    ruleIds: () => [] as number[]
  });

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const rowFlodMap = ref<Record<string, boolean>>({});
  const tableData = shallowRef<MysqlPermissonAccountModel[]>([]);

  const columns = computed(() => [
    {
      label: t('账号名称'),
      field: 'user',
      width: 220,
      showOverflowTooltip: false,
      render: ({ data }: { data: MysqlPermissonAccountModel }) => (
        <div class="account-box">
          {
            data.rules.length > 1
            && (
            <db-icon
              type="down-shape"
              class={{
                'flod-flag': true,
                'is-flod': rowFlodMap.value[data.account.user],
              }}
              onClick={() => handleToogleExpand(data.account.user)}/>
            )
          }
          { data.account.user }
        </div>
      ),
    },
    {
      label: t('访问的DB名'),
      width: 300,
      field: 'access_db',
      showOverflowTooltip: true,
      render: ({ data }: { data: MysqlPermissonAccountModel }) => {
        const renderRules = rowFlodMap.value[data.account.user] ? data.rules.slice(0, 1) : data.rules;
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
      field: 'privilege',
      showOverflowTooltip: false,
      render: ({ data }: { data: MysqlPermissonAccountModel }) => {
        if (data.rules.length === 0) {
          return <div class="inner-row">--</div>;
        }
        const renderRules = rowFlodMap.value[data.account.user] ? data.rules.slice(0, 1) : data.rules;
        return renderRules.map(item => (
          <div class="inner-row cell-privilege">
            <TextOverflowLayout>
              {{
                default: () => item.privilege
              }}
            </TextOverflowLayout>
          </div>
        ));
      },
    },
  ]);

  watch(
    () => props.ruleIds,
    () => {
      if (props.ruleIds.length > 0) {
        const accountType = props.clusterType === ClusterTypes.TENDBCLUSTER ? 'tendbcluster' : 'mysql';
        getPermissionRulesRun({
          bk_biz_id: currentBizId,
          rule_ids: props.ruleIds.join(','),
          account_type: accountType,
          offset: 0,
          limit: -1,
        });
      }
    },
  );

  const { run: getPermissionRulesRun, loading: isLoading } = useRequest(getPermissionRules, {
    manual: true,
    onSuccess({ results: permissionRulesResults }) {
      tableData.value = permissionRulesResults;
    },
  });

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
