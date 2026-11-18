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
  <div class="dns-domain-list">
    <div class="dns-domain-list-operations">
      <!-- 需求：持有 dns_domain_create 时展示，无权限不展示 -->
      <BkButton
        v-if="canCreate"
        class="w-88"
        theme="primary"
        @click="handleCreate">
        {{ t('新建域名') }}
      </BkButton>
      <BkCheckbox
        v-model="isMine"
        class="dns-domain-list-mine"
        @change="fetchData">
        {{ t('我负责的') }}
      </BkCheckbox>
      <DbQuickSearch
        v-model="searchValue"
        :data="searchData"
        parse-url
        style="width: 500px"
        @change="fetchData" />
    </div>
    <DbTable
      ref="table"
      :data-source="dataSource"
      releate-url-query
      :row-class-name="getRowClass"
      row-key="domain"
      @clear-search="handleClearSearch"
      @request-success="handleRequestSuccess">
      <TableColumn
        col-key="domain"
        :min-width="domainColumnWidth"
        :title="t('域名')">
        <template #default="{ row }: { row: DnsDomainModel }">
          <AuthButton
            action-id="dns_manage"
            :permission="row.permission.dns_manage"
            :resource="row.domain"
            text
            theme="primary"
            @click="handleOpenDetail(row)">
            {{ row.domain }}
          </AuthButton>
          <DbTag
            v-if="newDomainList.includes(row.domain)"
            class="ml-4"
            size="small"
            theme="success">
            NEW
          </DbTag>
        </template>
      </TableColumn>
      <TableColumn
        col-key="maintain_type"
        :min-width="150"
        :title="t('维护方式')">
        <template #default="{ row }: { row: DnsDomainModel }">
          {{ row.maintain_type_display || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="owners"
        :min-width="200"
        :title="t('负责人')">
        <template #default="{ row }: { row: DnsDomainModel }">
          <bk-user-display-name
            v-if="row.owners.length > 0"
            :user-id="row.owners.join(',')" />
          <span v-else>--</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="updater"
        :min-width="140"
        :title="t('更新人')">
        <template #default="{ row }: { row: DnsDomainModel }">
          <bk-user-display-name
            v-if="row.updater"
            :user-id="row.updater" />
          <span v-else>--</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="update_at"
        :min-width="180"
        :title="t('更新时间')">
        <template #default="{ row }: { row: DnsDomainModel }">
          {{ row.updateAtDisplay }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="row-operation"
        fixed="right"
        :title="t('操作')"
        :width="140">
        <template #default="{ row }: { row: DnsDomainModel }">
          <AuthButton
            v-if="row.isSelfMaintain"
            action-id="dns_manage"
            class="mr-8"
            :permission="row.permission.dns_manage"
            :resource="row.domain"
            text
            theme="primary"
            @click="handleOpenDetail(row)">
            {{ t('编辑') }}
          </AuthButton>
          <!-- 集群托管域名随集群生命周期维护，这里是业务只读，不是 IAM 无权限 -->
          <span
            v-else
            v-bk-tooltips="t('该域名由集群托管，请在对应集群中操作')"
            class="mr-8">
            <BkButton
              disabled
              text
              theme="primary">
              {{ t('编辑') }}
            </BkButton>
          </span>
          <AuthButton
            v-if="row.isSelfMaintain"
            action-id="dns_manage"
            :permission="row.permission.dns_manage"
            :resource="row.domain"
            text
            theme="primary"
            @click="handleDelete(row)">
            {{ t('删除') }}
          </AuthButton>
        </template>
      </TableColumn>
    </DbTable>
    <DomainCreate
      v-model:is-show="isShowCreate"
      @success="handleCreateSuccess" />
    <DomainDetail
      v-model:is-show="detailState.isShow"
      :domain="detailState.domain"
      @fail="fetchData"
      @success="fetchData" />
    <DomainDelete
      v-model:is-show="deleteState.isShow"
      :domain="deleteState.domain"
      @success="fetchData" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { IRequestPayload } from '@services/http';
  import DnsDomainModel from '@services/model/dns-domain/dns-domain';
  import { getDnsDomainList } from '@services/source/dnsDomain';

  import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import { searchUserRemoteMethod } from '@views/dns-domain/utils';

  import DomainCreate from './components/domain-create/Index.vue';
  import DomainDelete from './components/domain-delete/Index.vue';
  import DomainDetail from './components/domain-detail/Index.vue';

  const route = useRoute();
  const { t } = useI18n();

  const tableRef = useTemplateRef('table');

  // 域名类列按屏宽取档
  const domainColumnWidth = window.innerWidth < 1366 ? 180 : 280;

  // 「我负责的」随列表请求写进 URL，刷新时恢复
  const isMine = ref(route.query.mine === 'true');
  const searchValue = ref<Record<string, string>>({});
  const canCreate = ref(false);
  const isShowCreate = ref(false);

  const detailState = reactive({
    domain: '',
    isShow: false,
  });
  const deleteState = reactive({
    domain: '',
    isShow: false,
  });

  // 默认搜索字段排在首位：域名
  const searchData: QuickSearchProps['data'] = [
    {
      description: t('支持模糊搜索'),
      id: 'domain',
      name: t('域名'),
      type: 'input',
    },
    {
      id: 'maintain_type',
      list: [
        { label: t('自主维护'), value: 'self' },
        { label: t('集群托管'), value: 'cluster' },
      ],
      name: t('维护方式'),
      type: 'single',
    },
    {
      id: 'owner',
      name: t('负责人'),
      remoteMethod: searchUserRemoteMethod,
      remoteSearch: true,
      type: 'single',
    },
  ];

  // 本页新建的域名，最新的在前；只存内存，刷新页面即清空，列表恢复自然序
  const newDomainList = ref<string[]>([]);

  const dataSource = async (params: ServiceParameters<typeof getDnsDomainList>, payload: IRequestPayload) => {
    const data = await getDnsDomainList(params, payload);
    if (newDomainList.value.length < 1) {
      return data;
    }
    // 置顶行从自然序结果里剔除，避免同一域名出现两次
    const restResults = data.results.filter((item) => !newDomainList.value.includes(item.domain));
    if (params.offset) {
      return {
        ...data,
        results: restResults,
      };
    }
    // 首页：带上当前筛选条件逐个精确取回新建域名，不满足筛选的不置顶
    const pinnedResults = await Promise.all(
      newDomainList.value
        .filter((domain) => !params.domain || domain.includes(params.domain))
        .map((domain) =>
          getDnsDomainList({ ...params, domain, limit: 20, offset: 0 }, payload).then((result) =>
            result.results.find((item) => item.domain === domain),
          ),
        ),
    );
    return {
      ...data,
      results: [...pinnedResults.filter((item) => item !== undefined), ...restResults],
    };
  };

  const getRowClass = ({ row }: { row: DnsDomainModel }) => (newDomainList.value.includes(row.domain) ? 'is-new' : '');

  const fetchData = () => {
    tableRef.value!.fetchData({
      ...searchValue.value,
      // 未勾选时不传，避免 URL 上出现 mine=false
      mine: isMine.value ? true : undefined,
    });
  };

  const handleRequestSuccess = (data: ServiceReturnType<typeof getDnsDomainList>) => {
    canCreate.value = data.permission.dns_domain_create;
  };

  const handleClearSearch = () => {
    searchValue.value = {};
    isMine.value = false;
    fetchData();
  };

  const handleCreate = () => {
    isShowCreate.value = true;
  };

  const handleCreateSuccess = (domain: string) => {
    newDomainList.value = [domain, ...newDomainList.value.filter((item) => item !== domain)];
    fetchData();
  };

  const handleOpenDetail = (row: DnsDomainModel) => {
    detailState.domain = row.domain;
    detailState.isShow = true;
  };

  const handleDelete = (row: DnsDomainModel) => {
    deleteState.domain = row.domain;
    deleteState.isShow = true;
  };
</script>
<style lang="less">
  .dns-domain-list {
    .dns-domain-list-operations {
      display: flex;
      align-items: center;
      margin-bottom: 16px;

      .dns-domain-list-mine {
        margin-right: 16px;
        margin-left: auto;
      }
    }

    tbody {
      tr {
        &.is-new {
          td {
            background-color: #f3fcf5 !important;
          }
        }
      }
    }
  }
</style>
