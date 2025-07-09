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
  <InfoList>
    <InfoItem :label="t('目标集群')">
      <BkButton
        text
        theme="primary"
        @click="handleTargetCluster">
        <strong>{{ clusterIds.length }}</strong>
      </BkButton>
      <span>{{ t('个') }}</span>
    </InfoItem>
    <InfoItem :label="t('Excel 文件')">
      <div class="excel-link">
        <DbIcon
          class="mr-6"
          color="#2dcb56"
          svg
          type="excel" />
        <a :href="excelUrl">
          {{ t('批量授权文件') }}
          <DbIcon
            class="ml-6"
            svg
            type="import" />
        </a>
      </div>
    </InfoItem>
  </InfoList>
  <TargetClusterPreview
    v-model="previewTargetClusterShow"
    :cluster-ids="clusterIds"
    :title="t('目标集群预览')" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  import TargetClusterPreview from './components/TargetClusterPreview.vue';

  interface Props {
    ticketDetails: TicketModel<Mongodb.AuthorizeRules>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_EXCEL_AUTHORIZE_RULES,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const clusterIds = props.ticketDetails.details.authorize_data?.[0].cluster_ids || [];
  const excelUrl = props.ticketDetails.details?.excel_url;

  const previewTargetClusterShow = ref(false);

  const handleTargetCluster = () => {
    previewTargetClusterShow.value = true;
  };
</script>

<style lang="less" scoped>
  :deep(.excel-link) {
    display: flex;
    align-items: center;
  }

  :deep(.mongo-permission-cell) {
    position: relative;
    display: flex;
    height: 30px;
    padding: 0 15px;
    overflow: hidden;
    line-height: 30px;
    text-align: left;
    text-overflow: ellipsis;
    white-space: nowrap;
    border-bottom: 1px solid #dcdee5;
    align-items: center;
  }

  :deep(.mongo-permission-cell:last-child) {
    border-bottom: 0;
  }

  :deep(.user-icon) {
    position: absolute;
    top: 50%;
    left: 15px;
    transform: translateY(-50%) rotate(-90deg);
    transition: all 0.2s;
  }

  :deep(.user-icon-expand) {
    transform: translateY(-50%) rotate(0);
  }

  :deep(.user-name) {
    display: flex;
    height: 100%;
    padding-left: 24px;
    font-weight: bold;
    cursor: pointer;
    align-items: center;
  }

  :deep(.mongo-permission-table) {
    transition: all 0.5s;

    td {
      .vxe-cell {
        padding: 0 !important;
      }
    }

    td:first-child {
      .cell,
      .mongo-permission-cell {
        height: 100% !important;
      }
    }
  }
</style>
