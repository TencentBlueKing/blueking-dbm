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
      <div class="operations-left">
        <BkButton
          theme="primary"
          @click="handleCreate">
          {{ t('新建授权') }}
        </BkButton>
        <BkButton
          @click="handleExcelAuthorize">
          {{ t('Excel导入') }}
        </BkButton>
      </div>
      <DbSearchSelect
        v-model="tableSearch"
        :data="filters"
        :placeholder="t('请输入账号名称/DB名称/权限名称')"
        style="width: 500px;"
        unique-select
        @change="fetchTableData" />
    </div>
    <DbTable
      ref="tableRef"
      :columns="columns"
      :data-source="getPermissionRules"
      settings
      @clear-search="handleClearSearch" />
    <ClusterAuthorize
      v-model="authorizeShow"
      :access-dbs="authorizeDbs"
      :account-type="AccountTypes.TENDBCLUSTER"
      :cluster-types="[ClusterTypes.TENDBCLUSTER]"
      :user="authorizeUser" />
    <ExcelAuthorize
      v-model="isShowExcelAuthorize"
      :cluster-type="ClusterTypes.TENDBHA" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getPermissionRules } from '@services/permission';

  import {
    AccountTypes,
    ClusterTypes,
  } from '@common/const';

  import ClusterAuthorize from '@components/cluster-authorize/ClusterAuthorize.vue';

  import { dbOperations } from '../permission/common/consts';

  import ExcelAuthorize from './components/ExcelAuthorize.vue';

  import { useGlobalBizs } from '@/stores';
  import type { TableProps } from '@/types/bkui-vue';

  const tableSearch = ref([]);
  const authorizeShow = ref(false);
  const authorizeUser = ref('');
  const authorizeDbs = ref<string[]>([]);

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const tableRef = ref();

  onMounted(() => {
    fetchTableData();
  });

  const keyword = ref('');
  const columns: TableProps['columns'] = [
    {
      label: t('账号'),
      field: 'user',
    },
    {
      label: t('访问源'),
      field: 'ips',
      showOverflowTooltip: false,
    },
    {
      label: t('访问集群域名'),
      field: 'remark',
    },
    {
      label: t('访问DB'),
      field: 'access_db',
      showOverflowTooltip: false,
    },
    {
      label: t('权限'),
      field: 'privilege',
      showOverflowTooltip: false,
      filter: true,
    },
    {
      label: t('授权人'),
      field: 'updater',
      width: 180,
    },
    {
      label: t('授权时间'),
      field: 'update_at',
      width: 160,
      sort: true,
    },
  ];

  const filters = [
    {
      name: t('账号'),
      id: 'user',
    },
    {
      name: t('访问DB'),
      id: 'access_db',
    },
    {
      name: t('权限'),
      id: 'privilege',
      multiple: true,
      children: [
        ...dbOperations.dml.map(id => ({ id: id.toLowerCase(), name: id })),
        ...dbOperations.ddl.map(id => ({ id: id.toLowerCase(), name: id })),
        ...dbOperations.glob.map(id => ({ id, name: id })),
      ],
    },
  ];

  const fetchTableData = () => {
    tableRef.value.fetchData({
      ip: keyword.value,
      db_type: ClusterTypes.TENDBCLUSTER,
    }, {
      bk_biz_id: currentBizId,
    });
  };

  const handleClearSearch = () => {
    keyword.value = '';
    fetchTableData();
  };

  const handleCreate = () => {
    authorizeShow.value = true;
  };

  const isShowExcelAuthorize = ref(false);
  const handleExcelAuthorize = () => {
    isShowExcelAuthorize.value = true;
  };

</script>

<style lang="less" scoped>
.permission-list {
  .permission-list-operations {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 0;

    .operations-left {
      display: flex;
      align-items: center;

      .bk-button {
        min-width: 88px;
        margin-right: 8px;
      }
    }
  }

  :deep(.bk-table) {
    tr:hover {
      .copy-btn {
        display: inline-block;
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
