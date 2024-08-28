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
      <span class="slave-rebuild-types-title">
        {{ t('重建类型') }}
      </span>
      <div class="mt-8 mb-8">
        <CardCheckbox
          v-model="ticketType"
          :desc="t('在原主机上进行故障从库实例重建')"
          icon="rebuild"
          :title="t('原地重建')"
          true-value="TENDBCLUSTER_RESTORE_LOCAL_SLAVE" />
        <CardCheckbox
          v-model="ticketType"
          class="ml-8"
          :desc="t('将从库主机的全部实例重建到新主机')"
          icon="host"
          :title="t('新机重建')"
          true-value="TENDBCLUSTER_RESTORE_SLAVE" />
      </div>
    </div>
    <Component
      :is="renderCom"
      :ticket-clone-data="ticketCloneData" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { useTicketCloneInfo } from '@hooks';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import { createRowData as createNewHostRowData } from './components/new-host/components/render-data/Row.vue';
  import NewHost, { createDefaultFormData as createNewHostFormData } from './components/new-host/Index.vue';
  import { createRowData as createOriginHostRowData } from './components/original-host/components/RenderData/Row.vue';
  import OriginalHost, {
    createDefaultFormData as createOriginalHostFormData,
  } from './components/original-host/Index.vue';

  const { t } = useI18n();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.TENDBCLUSTER_RESTORE_LOCAL_SLAVE,
    onSuccess(cloneData) {
      ticketCloneData.value = cloneData;
      ticketType.value = TicketTypes.TENDBCLUSTER_RESTORE_LOCAL_SLAVE;
      window.changeConfirm = true;
    },
  });

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.TENDBCLUSTER_RESTORE_SLAVE,
    onSuccess(cloneData) {
      ticketCloneData.value = cloneData;
      ticketType.value = TicketTypes.TENDBCLUSTER_RESTORE_SLAVE;
      window.changeConfirm = true;
    },
  });

  const comMap = {
    TENDBCLUSTER_RESTORE_LOCAL_SLAVE: {
      content: OriginalHost,
      createRowData: createOriginHostRowData,
      createDefaultFormData: createOriginalHostFormData,
    },
    TENDBCLUSTER_RESTORE_SLAVE: {
      content: NewHost,
      createRowData: createNewHostRowData,
      createDefaultFormData: createNewHostFormData,
    },
  };

  const ticketType = ref<keyof typeof comMap>('TENDBCLUSTER_RESTORE_LOCAL_SLAVE');
  const ticketCloneData = ref();

  const renderCom = computed(() => comMap[ticketType.value].content);

  watch(ticketType, () => {
    const currentComponent = comMap[ticketType.value];
    Object.assign(ticketCloneData, {
      tableDataList: [currentComponent.createDefaultFormData()],
      formData: currentComponent.createDefaultFormData(),
    });
  });
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
        font-weight: 700;

        &::after {
          position: absolute;
          top: 2px;
          right: -8px;
          color: @danger-color;
          content: '*';
        }
      }
    }
  }
</style>
