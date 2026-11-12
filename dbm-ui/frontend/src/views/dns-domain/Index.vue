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
  <div class="dns-domain-page">
    <div class="dns-domain-nav">
      <div
        class="dns-domain-nav-item"
        :class="{ 'is-active': currentPage === 'domains' }"
        @click="handlePageChange('domains')">
        {{ t('域名列表') }}
      </div>
      <!-- 全局日志入口常驻，无 dns_audit_view 时置灰加锁，点击申请权限；权限取列表接口的 can_view_global_audit，不单独鉴权 -->
      <AuthTemplate
        action-id="dns_audit_view"
        class="dns-domain-nav-auth"
        :permission="canViewGlobalAudit">
        <div
          class="dns-domain-nav-item"
          :class="{ 'is-active': currentPage === 'audits' }"
          @click="handlePageChange('audits')">
          {{ t('操作日志') }}
        </div>
      </AuthTemplate>
    </div>
    <div class="dns-domain-main">
      <DomainList v-if="currentPage === 'domains'" />
      <AuditTable
        v-else
        scope="global" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getDnsDomainList } from '@services/source/dnsDomain';

  import AuditTable from './components/audit-table/Index.vue';
  import DomainList from './components/domain-list/Index.vue';

  type PageType = 'domains' | 'audits';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  // 全局日志查看权限，接口返回前按无权限展示
  const canViewGlobalAudit = ref(false);

  // 页面内导航由路由参数 page 驱动，刷新后保持
  const currentPage = computed<PageType>(() => (route.params.page === 'audits' ? 'audits' : 'domains'));

  // 列表接口同时返回入口权限，只取 1 条；失败时保持置灰，不弹全局提示
  getDnsDomainList({ limit: 1, offset: 0 }, { catchError: true }).then((data) => {
    canViewGlobalAudit.value = data.can_view_global_audit;
  });

  const handlePageChange = (page: PageType) => {
    if (page === currentPage.value) {
      return;
    }
    // 两个页面的筛选条件互不相干，切换时清空 query
    router.replace({
      name: 'DnsDomain',
      params: {
        page,
      },
      query: {},
    });
  };
</script>
<style lang="less">
  .dns-domain-page {
    display: flex;
    height: 100%;

    .dns-domain-nav {
      width: 200px;
      padding: 8px 0;
      background: #fff;
      border-right: 1px solid #dcdee5;
      flex-shrink: 0;

      .dns-domain-nav-auth {
        display: block;
      }

      .dns-domain-nav-item {
        height: 40px;
        padding: 0 24px;
        font-size: 14px;
        line-height: 40px;
        color: #63656e;
        cursor: pointer;

        &:hover {
          background: #f5f7fa;
        }

        &.is-active {
          color: #3a84ff;
          background: #e1ecff;
        }
      }
    }

    .dns-domain-main {
      padding: 20px 24px 0;
      overflow: hidden;
      flex: 1;
    }
  }
</style>
