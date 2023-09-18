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
  <div class="deployment-plan-list-page">
    <BkTab
      v-model:active="tabActive"
      class="header-tab"
      type="unborder-card">
      <BkTabPanel
        label="TendisCache"
        name="TendisCache" />
      <BkTabPanel
        label="TendisPlus"
        name="TendisPlus" />
      <BkTabPanel
        label="TendisSSD"
        name="TendisSSD" />
    </BkTab>
    <div class="content-wrapper">
      <div class="mb-12">
        <BkButton
          class="w88"
          theme="primary"
          @click="handleShowEdit">
          新建
        </BkButton>
        <BkButton class="ml-8 w88">
          删除
        </BkButton>
      </div>
      <DbTable :columns="tableColumn" />
    </div>
  </div>
  <BkSideslider
    v-model:is-show="isShowOperation"
    :title="t('新建方案')"
    width="960">
    <PlanOperation />
  </BkSideslider>
</template>
<script setup lang="tsx">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import PlanOperation from './components/Operation.vue';

  const { t } = useI18n();

  const tabActive = ref('');
  const isShowOperation = ref(false);

  const tableColumn = [
    {
      label: t('方案名称'),
      field: 'id',
      fixed: 'left',
      width: 100,
    },
    {
      label: t('存储类型'),
      field: 'id',
    },
    {
      label: t('集群分片数'),
      field: 'id',
      width: 100,
    },
    {
      label: t('Proxy 资源规格（机器数量）'),
      field: 'id',
      width: 170,
    },
    {
      label: t('后端存储资源规格（机器数量）'),
      field: 'id',
      width: 190,
    },
    {
      label: t('集群预估容量（G）'),
      field: 'id',
      width: 150,
    },
    {
      label: t('更新时间'),
      field: 'id',
      width: 100,
    },
    {
      label: t('更新人'),
      field: 'id',
      width: 100,
    },
    {
      label: t('操作'),
      render: () => (
        <>
          <bk-button text>编辑</bk-button>
          <bk-button
            text
            class="ml-8">
            克隆
          </bk-button>
          <bk-button
            class="ml-8"
            text>
            删除
          </bk-button>
        </>
      ),
    },
  ];

  const handleShowEdit = () => {
    isShowOperation.value = true;
  };
</script>
<style lang="less">
  .deployment-plan-list-page {
    display: block;
    margin: -24px;

    .header-tab {
      z-index: 99;
      background: #fff;

      .bk-tab-content {
        display: none;
      }
    }

    .content-wrapper {
      padding: 24px;
    }
  }
</style>
