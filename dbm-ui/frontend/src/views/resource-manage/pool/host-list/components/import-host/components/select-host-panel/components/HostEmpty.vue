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
  <div class="export-host-empty">
    <BkException
      scene="part"
      type="empty" />
    <div style="display: inline-block; text-align: left">
      <div class="mb-12">
        {{ t('暂无主机，你通过以下方法获取主机至“DBA 业务  -> 空闲机池  -> 空闲机模块”') }}
      </div>
      <div>
        <I18nT keypath="方法一：从CMDB 资源池分配；">
          <a
            :href="data?.bk_cmdb_url"
            target="_blank">
            {{ t('CMDB 资源池') }}
          </a>
        </I18nT>
      </div>
      <div>
        <I18nT keypath="方法二：从节点管理导入安装；">
          <a
            :href="data?.bk_nodeman_url"
            target="_blank">
            {{ t('节点管理导入') }}
          </a>
        </I18nT>
      </div>
      <div>
        <I18nT keypath="方法三：内网环境下，通过SCR 系统申请资源；">
          <a
            :href="data?.bk_scr_url"
            target="_blank">
            {{ t('SCR 系统申请') }}
          </a>
        </I18nT>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchResourceImportUrls } from '@services/source/dbresourceResource';

  const { t } = useI18n();

  const { data } = useRequest(fetchResourceImportUrls);
</script>
<style lang="less" scoped>
  .export-host-empty {
    width: 100%;
    font-size: 14px;
    line-height: 28px;
    color: #63656e;
    text-align: center;
  }
</style>
