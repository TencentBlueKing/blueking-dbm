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
  <BkAlert
    class="mb-20"
    closable
    :title="t('重建从库_原机器或新机器重新同步数据及权限_并且将域名解析指向同步好的机器')" />
  <div>
    <strong class="restore-types-title">
      {{ t('重建类型') }}
    </strong>
    <div class="mt-8 mb-20">
      <CardCheckbox
        v-model="restoreType"
        :desc="t('在原主机上进行故障从库实例重建')"
        icon="rebuild"
        :title="t('原地重建')"
        :true-value="RestoreTypes.LOCAL_RESTORE" />
      <CardCheckbox
        v-model="restoreType"
        class="ml-8"
        :desc="t('将从库主机的全部实例重建到新主机')"
        icon="host"
        :title="t('新机重建')"
        :true-value="RestoreTypes.RESTORE" />
    </div>
  </div>
  <Component :is="comMap[restoreType]" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import LocalRestore from './components/local-restore/Index.vue';
  import Restore from './components/restore/Index.vue';

  /**
   * INSTANCE_REPLACE: 原地重建
   * HOST_REPLACE: 新机重建
   */
  enum RestoreTypes {
    LOCAL_RESTORE = 'LOCAL_RESTORE',
    RESTORE = 'RESTORE',
  }

  const { t } = useI18n();

  const comMap = {
    [RestoreTypes.LOCAL_RESTORE]: LocalRestore,
    [RestoreTypes.RESTORE]: Restore,
  };

  const restoreType = ref(RestoreTypes.LOCAL_RESTORE);
</script>

<style lang="less" scoped>
  .restore-types-title {
    position: relative;
    font-size: @font-size-mini;
    color: @title-color;

    &::after {
      position: absolute;
      top: 2px;
      right: -8px;
      color: @danger-color;
      content: '*';
    }
  }
</style>
