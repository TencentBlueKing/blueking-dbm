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
  <div class="permission-list">
    <div class="permission-list-operations">
      <div class="permission-list-operations__left">
        <BkButton
          theme="primary"
          @click="handleCreate">
          {{ $t('新建授权') }}
        </BkButton>
        <BkButton
          @click="handleExport">
          {{ $t('Excel导入') }}
        </BkButton>
      </div>
      <DbSearchSelect
        v-model="state.search"
        :data="filters"
        :placeholder="$t('请输入账号名称/DB名称/权限名称')"
        style="width: 500px;"
        unique-select
        @change="getList" />
    </div>
    <DbTable
      ref="tableRef"
      :columns="columns"
      :data-source="getList"
      settings
      @clear-search="handleClearSearch" />
    <ClusterAuthorize
      v-model:is-show="authorizeState.isShow"
      :access-dbs="authorizeState.dbs"
      :cluster-type="ClusterTypes.TENDBCLUSTER"
      :ticket-type="TicketTypes.TENDBCLUSTER_AUTHORIZE_RULES"
      :user="authorizeState.user" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { useCopy, useInfoWithIcon, useTableMaxHeight   } from '@hooks';

  import { ClusterTypes, DBTypes, OccupiedInnerHeight, TicketTypes } from '@common/const';

  import ClusterAuthorize from '@components/cluster-authorize/ClusterAuthorize.vue';
  import RenderRow from '@components/render-row/index.vue';

  import { messageSuccess } from '@utils';

  import { dbOperations } from '../permission/common/consts';
  import type { PermissionState, PermissionTableRow } from '../permission/common/types';
  import { getRenderList, isNewUser } from '../permission/common/utils';

  import { usePermissionList } from './hooks/usePermissionList';

  import { useGlobalBizs } from '@/stores';
  import type { TableProps } from '@/types/bkui-vue';

  const state = reactive({
    isAnomalies: false,
    isLoading: false,
    search: [],
    data: [],
  });

  const authorizeState = reactive({
    isShow: false,
    user: '',
    dbs: [] as string[],
  });
  const { getList } = usePermissionList(state);

  const { currentBizId } = useGlobalBizs();
  const copy = useCopy();
  const { t } = useI18n();
  const tableRef = ref();


  const tableMaxHeight = useTableMaxHeight(OccupiedInnerHeight.NOT_PAGINATION);
  const setRowClass = (row: PermissionTableRow) => (isNewUser(row) ? 'is-new' : '');

  const keyword = ref('');
  const columns: TableProps['columns'] = [
    {
      label: t('账号'),
      field: 'ips',
    },
    {
      label: t('访问源'),
      field: 'ips',
      showOverflowTooltip: false,
      render: ({ rules }: PermissionTableRow) => (
          <>
            <span>{ rules[0].privilege }</span>
            <db-icon v-bk-tooltips={t('复制')} type="copy copy-btn" onClick={copy.bind(null, rules[0].privilege)} />
          </>
        ),
    }, {
      label: t('访问集群域名'),
      field: 'remark',
      render: ({ rules }: PermissionTableRow) => (
          <>
            <span>{ rules[0].privilege }</span>
            <db-icon v-bk-tooltips={t('复制')} type="copy copy-btn" onClick={copy.bind(null, rules[0].privilege)} />
          </>
        ),
    }, {
      label: t('访问DB'),
      field: 'access_db',
      showOverflowTooltip: false,
      render: ({ data }: { data: PermissionTableRow }) => (
        getRenderList(data).map((rule) => {
          const { privilege } = rule;

          return (
            <div class="permission__cell" v-overflow-tips>
              {
                !privilege ? '--' : privilege.replace(/,/g, '，')
              }
            </div>
          );
        })
      ),
    }, {
      label: t('权限'),
      field: 'privilege',
      showOverflowTooltip: false,
      filter: true,
      render: ({ data }: { data: PermissionTableRow }) => {
        const { privilege } = data.rules[0];
        return (
            <RenderRow style={'max-width: calc(100% - 20px'} data={privilege.split(',')} />
        );
      },
    }, {
      label: t('授权人'),
      field: 'updater',
      width: 180,
    }, {
      label: t('授权时间'),
      field: 'update_at',
      width: 160,
      sort: true,
    },
  ];

  const filters = [{
    name: t('账号'),
    id: 'user',
  }, {
    name: t('访问DB'),
    id: 'access_db',
  }, {
    name: t('权限'),
    id: 'privilege',
    multiple: true,
    children: [
      ...dbOperations.dml.map(id => ({ id: id.toLowerCase(), name: id })),
      ...dbOperations.ddl.map(id => ({ id: id.toLowerCase(), name: id })),
      ...dbOperations.glob.map(id => ({ id, name: id })),
    ],
  }];

  const fetchTableData = () => {
    tableRef.value.fetchData({
      ip: keyword.value,
      db_type: DBTypes.TENDBCLUSTER,
    }, {
      bk_biz_id: currentBizId,
    });
  };

  const handleClearSearch = () => {
    keyword.value = '';
    fetchTableData();
  };

  const handleCreate = () => {
    authorizeState.isShow = true;
  };

  const handleExport = () => {
    //
  };

</script>

<style lang="less" scoped>
.permission-list {
  &-operations {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 0;

    &__left {
      display: flex;
      align-items: center;

      .bk-button {
        min-width: 88px;
        margin-right: 8px;
      }
    }
  }

  :deep(.bk-table) {
    tr {
      &:hover {
        .copy-btn {
          display: inline-block;
        }
      }
    }

    .copy-btn {
      display: none;
      margin-left: 8px;
      color: @primary-color;
      cursor: pointer;
    }
  }
}
</style>
