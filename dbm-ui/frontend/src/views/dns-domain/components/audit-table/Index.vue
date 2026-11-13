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
  <ApplyPermissionCatch>
    <div class="dns-domain-audit-table">
      <div class="dns-domain-audit-operations">
        <BkButton
          class="w-88"
          :loading="isExporting"
          @click="handleExport">
          {{ t('导出') }}
        </BkButton>
        <DbQuickSearch
          v-model="searchValue"
          class="dns-domain-audit-search"
          :data="searchData"
          :parse-url="isGlobal"
          @change="fetchData" />
      </div>
      <DbTable
        ref="table"
        :data-source="dataSource"
        :releate-url-query="isGlobal"
        row-key="id"
        @clear-search="handleClearSearch">
        <TableColumn
          col-key="create_at"
          :min-width="180"
          :title="t('时间')">
          <template #default="{ row }: { row: DnsDomainAuditModel }">
            {{ row.create_at || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="operator"
          :min-width="140"
          :title="t('操作人')">
          <template #default="{ row }: { row: DnsDomainAuditModel }">
            <bk-user-display-name
              v-if="row.operator"
              :user-id="row.operator" />
            <span v-else>--</span>
          </template>
        </TableColumn>
        <TableColumn
          col-key="client_ip"
          :min-width="140"
          :title="t('客户端 IP')">
          <template #default="{ row }: { row: DnsDomainAuditModel }">
            {{ row.client_ip || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="action"
          :min-width="150"
          :title="t('操作类型')">
          <template #default="{ row }: { row: DnsDomainAuditModel }">
            {{ row.action_display || '--' }}
          </template>
        </TableColumn>
        <!-- 全局日志在操作类型后增加域名列 -->
        <TableColumn
          v-if="isGlobal"
          col-key="domain"
          :min-width="domainColumnWidth"
          :title="t('域名')">
          <template #default="{ row }: { row: DnsDomainAuditModel }">
            {{ row.domain || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="change_lines"
          :ellipsis="false"
          :min-width="280"
          :title="t('变更内容')">
          <template #default="{ row }: { row: DnsDomainAuditModel }">
            <template v-if="row.change_lines.length > 0">
              <div
                v-for="(line, index) in row.change_lines"
                :key="index"
                class="dns-domain-audit-change-line">
                {{ line }}
              </div>
            </template>
            <span v-else>--</span>
          </template>
        </TableColumn>
      </DbTable>
    </div>
  </ApplyPermissionCatch>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { IRequestPayload } from '@services/http';
  import DnsDomainAuditModel from '@services/model/dns-domain/dns-domain-audit';
  import { type DnsDomainAuditScope, exportDnsDomainAudits, getDnsDomainAudits } from '@services/source/dnsDomain';

  import ApplyPermissionCatch from '@components/apply-permission/Catch.vue';
  import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import { searchUserRemoteMethod } from '@views/dns-domain/utils';

  interface Props {
    // 本域日志的完整域名，scope 为 domain 时必传
    domain?: string;
    scope: DnsDomainAuditScope;
  }

  interface Exposes {
    // 按当前筛选与页码原地刷新
    refresh: () => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    domain: '',
  });

  const { t } = useI18n();

  const tableRef = useTemplateRef('table');

  const isGlobal = props.scope === 'global';
  // 域名类列按屏宽取档
  const domainColumnWidth = window.innerWidth < 1366 ? 180 : 280;

  const searchValue = ref<Record<string, string>>({});
  const isExporting = ref(false);

  const actionSearchItem = {
    id: 'action',
    list: [
      { label: t('创建域名'), value: 'create' },
      { label: t('修改 IP'), value: 'update_ip' },
      { label: t('修改备注'), value: 'update_remark' },
      { label: t('修改负责人'), value: 'update_owner' },
      { label: t('删除域名'), value: 'delete' },
    ],
    name: t('操作类型'),
    type: 'single' as const,
  };
  const operatorSearchItem = {
    id: 'operator',
    name: t('操作人'),
    remoteMethod: searchUserRemoteMethod,
    remoteSearch: true,
    type: 'single' as const,
  };

  /**
   * 默认搜索字段排在首位：本域为操作人，全局为域名。
   * 全局的域名条件走接口的 keyword（全局 keyword 匹配域名），id 与接口参数一致，URL 回填时才能对上
   */
  const searchData: QuickSearchProps['data'] = isGlobal
    ? [
        {
          description: t('支持模糊搜索'),
          id: 'keyword',
          name: t('域名'),
          type: 'input',
        },
        operatorSearchItem,
        actionSearchItem,
      ]
    : [operatorSearchItem, actionSearchItem];

  const baseParams = computed(() => ({
    scope: props.scope,
    ...(isGlobal ? {} : { domain: props.domain }),
  }));

  const dataSource = (params: ServiceParameters<typeof getDnsDomainAudits>, payload: IRequestPayload) =>
    getDnsDomainAudits(
      {
        ...params,
        ...baseParams.value,
      },
      // 全局日志无权限时在本区域展示申请，保留左侧菜单
      isGlobal ? { ...payload, permission: 'catch' } : payload,
    );

  const fetchData = () => {
    tableRef.value!.fetchData({
      ...searchValue.value,
    });
  };

  const handleClearSearch = () => {
    searchValue.value = {};
    fetchData();
  };

  // 导出当前筛选的全部匹配
  const handleExport = () => {
    isExporting.value = true;
    exportDnsDomainAudits({
      ...searchValue.value,
      ...baseParams.value,
    }).finally(() => {
      isExporting.value = false;
    });
  };

  defineExpose<Exposes>({
    // 本域日志未开启 URL 联动，查询条件不变时 DbTable 保留当前页码
    refresh: fetchData,
  });
</script>
<style lang="less">
  .dns-domain-audit-table {
    .dns-domain-audit-operations {
      display: flex;
      align-items: center;
      margin-bottom: 16px;

      .dns-domain-audit-search {
        width: 500px;
        margin-left: auto;
      }
    }

    .dns-domain-audit-change-line {
      line-height: 20px;
      word-break: break-all;
    }
  }
</style>
