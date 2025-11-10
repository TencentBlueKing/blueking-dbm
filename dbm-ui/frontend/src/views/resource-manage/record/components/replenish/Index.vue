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
  <div class="replenish-record-page">
    <div class="header-action">
      <div>
        <BkRadioGroup
          v-model="activeTab"
          type="capsule">
          <BkRadioButton label="operation-view">
            <DbIcon
              class="mr-4"
              type="bk-dbm-icon db-icon-legend" />
            {{ t('补货操作视角') }}
          </BkRadioButton>
          <BkRadioButton label="ticket-view">
            <DbIcon
              class="mr-4"
              type="bk-dbm-icon db-icon-danju" />
            {{ t('补货单据视角') }}
          </BkRadioButton>
        </BkRadioGroup>
        <BkButton
          class="ml-12 forward-btn"
          text
          theme="primary"
          @click="handleForward">
          {{ t('跳转待补货列表') }}
          <DbIcon
            class="ml-6"
            type="bk-dbm-icon db-icon-link" />
        </BkButton>
      </div>
      <div class="header-filters">
        <DbDateTimePicker
          class="date-time-picker mr-8"
          clearable
          mode="previous"
          @change="handleDateTimeClear"
          @finish="handleDateTimePick" />
        <DbQuickSearch
          v-model="quickSearchValue"
          :data="quickSearchData"
          :placeholder="t('搜索 ID，DB 类型，申请人')"
          style="width: 450px"
          @change="handleSearchValueChange" />
      </div>
    </div>
    <div class="replenish-record-list">
      <KeepAlive>
        <Component
          :is="renderComponentMap[activeTab]"
          :key="activeTab"
          ref="tableRef" />
      </KeepAlive>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import OperationView from './components/operation-view/Index.vue';
  import TicketView from './components/ticket-view/Index.vue';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const renderComponentMap = {
    'operation-view': OperationView,
    'ticket-view': TicketView,
  };

  const URL_REPLENISH_MEMO_KEY = '__replenish_payload__';

  const quickSearchData = [
    {
      id: 'id',
      name: 'ID',
    },
    {
      id: 'db_type',
      name: t('DB 类型'),
    },
    {
      id: 'creator',
      name: t('申请人'),
    },
  ];

  const tableRef = ref();
  const quickSearchValue = ref<Record<string, any>>({});
  const activeTab = ref<keyof typeof renderComponentMap>('operation-view');
  // 缓存变更，减少多余请求
  let timeCache: [string, string] = ['', ''];
  // const searchCache: Record<string, any> = {};

  const handleDateTimeClear = (value: [string, string]) => {
    if (_.isEqual(timeCache, value)) {
      return;
    }
    const [start, end] = value;
    if (!start && !end) {
      tableRef.value?.fetchData();
    }
    timeCache = value;
  };

  const handleDateTimePick = (value: [string, string]) => {
    const [start, end] = value;
    tableRef.value?.fetchData({
      create_at__gte: start || undefined,
      create_at__lte: end || undefined,
    });
  };

  const handleSearchValueChange = (payload: Record<string, string>) => {
    tableRef.value?.fetchData(payload);
    router.replace({
      query: {
        ...payload,
        [URL_REPLENISH_MEMO_KEY]: encodeURIComponent(JSON.stringify(payload)),
      },
    });
  };

  const handleForward = () => {
    router.push({
      name: 'resourcePool',
      params: {
        page: 'replenish-list',
      },
    });
  };

  onMounted(() => {
    const urlPaylaod = JSON.parse(decodeURIComponent(String(route.query[URL_REPLENISH_MEMO_KEY] || '{}')));
    quickSearchValue.value = urlPaylaod;
  });

  onBeforeUnmount(() => {
    quickSearchValue.value = {};
  });
</script>
<style lang="less">
  .replenish-record-page {
    .bk-radio-button-label {
      font-size: 12px;
      line-height: 20px;
      display: flex;
      align-items: center;
    }

    .header-action {
      display: flex;
      align-items: center;
      padding-bottom: 16px;
      justify-content: space-between;
    }

    .forward-btn {
      font-size: 12px;
      position: relative;
      top: 2px;

      .db-icon-bk-dbm-icon {
        position: relative;
        top: 2px;
      }
    }

    .header-filters {
      display: flex;
      align-items: center;

      .date-time-picker {
        width: 320px !important;
      }
    }

    .replenish-record-list {
      font-family: MicrosoftYaHei;
      background: #fff;
      box-shadow: 0 2px 4px 0 rgba(25, 25, 41, 0.05);

      .bold-number {
        font-family: MicrosoftYaHei-Bold;
        font-weight: 700;
        font-size: 12px;
        color: #4d4f56;
        letter-spacing: 0;
        line-height: 20px;
        margin: 0px 2px;
      }

      .green-number {
        color: #2caf5e;
      }

      .red-number {
        color: #ea3636;
      }

      .table-footer {
        padding: 14px 16px;
        position: relative;
        z-index: 1;
        display: flex;
        height: 60px;
        padding: 0 16px;
        margin-top: -1px;
        background: #fff;
        border-top: 1px solid var(--td-component-border);
        align-items: center;

        .bk-pagination {
          width: 100%;

          & > .is-last {
            margin-left: auto;
          }
        }
      }
    }
  }
</style>
