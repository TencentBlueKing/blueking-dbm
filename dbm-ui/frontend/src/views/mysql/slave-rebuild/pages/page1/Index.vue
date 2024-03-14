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
  <div class="slave-rebuild-page">
    <BkAlert
      closable
      :title="t('重建从库_原机器或新机器重新同步数据及权限_并且将域名解析指向同步好的机器')" />
    <div class="slave-rebuild-types">
      <strong class="slave-rebuild-types-title">
        {{ t('重建类型') }}
      </strong>
      <div class="mt-8 mb-8">
        <CardCheckbox
          v-model="ticketType"
          :desc="t('在原主机上进行故障从库实例重建')"
          icon="rebuild"
          :title="t('原地重建')"
          true-value="MYSQL_RESTORE_LOCAL_SLAVE" />
        <CardCheckbox
          v-model="ticketType"
          class="ml-8"
          :desc="t('将从库主机的全部实例重建到新主机')"
          icon="host"
          :title="t('新机重建')"
          true-value="MYSQL_RESTORE_SLAVE" />
      </div>
    </div>
    <Component :is="renderCom" />
  </div>
</template>
<script setup lang="tsx">
  import {
    computed,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import NewHost from './components/new-host/Index.vue';
  import OriginalHost from './components/original-host/Index.vue';

  const { t } = useI18n();

  const comMap = {
    MYSQL_RESTORE_LOCAL_SLAVE: OriginalHost,
    MYSQL_RESTORE_SLAVE: NewHost,
  };

  const ticketType = ref<keyof typeof comMap>('MYSQL_RESTORE_LOCAL_SLAVE');

  const renderCom = computed(() => comMap[ticketType.value]);
</script>
<style lang="less">
  .slave-rebuild-page {
    height: 100%;
    padding-bottom: 20px;
    overflow: hidden;

    .slave-rebuild-types {
      margin-top: 24px;

      .slave-rebuild-types-title {
        position: relative;
        font-size: @font-size-mini;
        color: @title-color;

        &::after {
          position: absolute;
          top: 2px;
          right: -8px;
          color: @danger-color;
          content: "*";
        }
      }
    }
  }
</style>
