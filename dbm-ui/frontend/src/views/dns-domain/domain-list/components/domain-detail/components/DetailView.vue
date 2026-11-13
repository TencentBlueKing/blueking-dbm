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
  <div class="dns-domain-detail-view">
    <BkAlert
      class="mb-16"
      theme="info"
      :title="data.readonly_reason || t('该域名由集群托管，请在对应集群中操作')" />
    <div class="dns-domain-detail-kv">
      <div
        v-for="item in infoList"
        :key="item.label"
        class="dns-domain-detail-kv-item">
        <span class="dns-domain-detail-kv-label">{{ item.label }}：</span>
        <span class="dns-domain-detail-kv-value">
          <bk-user-display-name
            v-if="item.isUser && item.value"
            :user-id="item.value" />
          <template v-else>{{ item.value || '--' }}</template>
        </span>
      </div>
    </div>
    <div class="dns-domain-detail-ips">
      <span class="dns-domain-detail-kv-label">IP：</span>
      <div class="dns-domain-detail-ip-list">
        <template v-if="data.ips.length > 0">
          <DbTag
            v-for="ip in data.ips"
            :key="ip">
            {{ ip }}
          </DbTag>
        </template>
        <span v-else>--</span>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { DnsDomainDetail } from '@services/source/dnsDomain';

  interface Props {
    data: DnsDomainDetail;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const infoList = computed(() => [
    { label: t('域名'), value: props.data.domain },
    { label: t('维护方式'), value: props.data.maintain_type_display },
    { isUser: true, label: t('负责人'), value: props.data.owners.join(',') },
    { label: t('备注'), value: props.data.remark },
  ]);
</script>
<style lang="less">
  .dns-domain-detail-view {
    font-size: 12px;

    .dns-domain-detail-kv {
      display: flex;
      flex-wrap: wrap;
    }

    .dns-domain-detail-kv-item {
      display: flex;
      width: 50%;
      line-height: 32px;
    }

    .dns-domain-detail-kv-label {
      width: 80px;
      padding-right: 8px;
      color: #4d4f56;
      text-align: right;
      flex-shrink: 0;
    }

    .dns-domain-detail-kv-value {
      color: #313238;
      word-break: break-all;
    }

    .dns-domain-detail-ips {
      display: flex;
      line-height: 32px;
    }

    .dns-domain-detail-ip-list {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      align-items: center;
    }
  }
</style>
