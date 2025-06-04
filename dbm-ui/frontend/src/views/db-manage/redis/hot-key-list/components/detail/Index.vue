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
  <BkSideslider
    v-model:is-show="isShow"
    quick-close
    :width="960">
    <template #header>
      <div class="hot-key-list-detail-header">
        <span>{{ t('热 Key 分析报告') }}</span>
        <template v-if="currentRecord">
          <span class="header-info ml-8"> {{ currentRecord.root_id }}（{{ currentRecord.immute_domain }}） </span>
          <BkButton
            class="ml-8"
            :disabled="tableList.length === 0"
            @click="handleExport">
            <DbIcon
              class="mr-4"
              type="daochu" />
            {{ t('导出') }}
          </BkButton>
        </template>
        <BkButton
          v-bk-tooltips="t('上一条')"
          :disabled="currentIndex === 0 || getAnalysisDetailsLoading"
          style="width: 32px; margin-left: auto"
          @click="handleCurrentIndexChange(false)">
          <DbIcon type="up-big" />
        </BkButton>
        <BkButton
          v-bk-tooltips="t('下一条')"
          class="ml-8"
          :disabled="currentIndex === recordList.length - 1 || getAnalysisDetailsLoading"
          style="width: 32px"
          @click="handleCurrentIndexChange">
          <DbIcon type="down-big" />
        </BkButton>
      </div>
    </template>
    <template #default>
      <div class="hot-key-list-detail-content">
        <div class="filter-box">
          <BkSelect
            v-model="selectedInstanceList"
            collapse-tags
            filterable
            multiple
            multiple-mode="tag"
            style="width: 400px"
            @change="() => fetchData()">
            <BkOption
              v-for="item in instanceList"
              :id="item"
              :key="item"
              :name="item" />
          </BkSelect>
          <BkInput
            v-model="serachKey"
            class="ml-8"
            clearable
            :placeholder="t('请输入 Key 进行搜索')"
            style="flex: 1"
            type="search"
            @clear="() => fetchData()"
            @enter="() => fetchData()" />
        </div>
        <BkLoading :loading="getAnalysisDetailsLoading">
          <template v-if="tableList.length > 0">
            <Info
              v-for="item in tableList"
              :key="item.instace"
              :info="item" />
          </template>
          <EmptyStatus
            v-else
            :is-anomalies="!!getAnalysisDetailsError"
            is-searching
            @clear-search="handleClearSearch"
            @refresh="() => fetchData()" />
        </BkLoading>
      </div>
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RedisHotKeyModel from '@services/model/redis/redis-hot-key';
  import { exportHotKeyAnalysis, getAnalysisDetails } from '@services/source/redisAnalysis';

  import { useDebouncedRef } from '@hooks';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import Info from './components/Info.vue';

  interface Props {
    recordList: RedisHotKeyModel[];
  }

  const props = defineProps<Props>();
  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });
  const currentIndex = defineModel<number>('currentIndex', {
    required: true,
  });

  const { t } = useI18n();

  const serachKey = useDebouncedRef('');
  const selectedInstanceList = ref<string[]>([]);

  const currentRecord = computed(() => props.recordList[currentIndex.value]);
  const instanceList = computed(() => currentRecord.value.ins_list);

  const tableList = computed(() =>
    Object.entries(detailData.value || {}).map(([key, item]) => ({
      infos: item,
      instace: key,
    })),
  );

  const {
    data: detailData,
    error: getAnalysisDetailsError,
    loading: getAnalysisDetailsLoading,
    run: runGetAnalysisDetails,
  } = useRequest(getAnalysisDetails, {
    debounceInterval: 200,
    manual: true,
  });

  watch(
    currentRecord,
    () => {
      selectedInstanceList.value = currentRecord.value.ins_list;
      serachKey.value = '';
      fetchData();
    },
    // {
    //   immediate: true,
    // },
  );

  watch(serachKey, () => {
    fetchData();
  });

  const handleCurrentIndexChange = (isNext = true) => {
    if (isNext) {
      currentIndex.value = currentIndex.value + 1;
    } else {
      currentIndex.value = currentIndex.value - 1;
    }
  };

  const handleClearSearch = () => {
    selectedInstanceList.value = [];
    serachKey.value = '';
    fetchData();
  };

  const fetchData = () => {
    runGetAnalysisDetails({
      instance_addresses: selectedInstanceList.value.join(','),
      key: serachKey.value,
      limit: -1,
      offset: 0,
      record_id: currentRecord.value.id,
    });
  };

  const handleExport = () => {
    exportHotKeyAnalysis({
      instance_addresses: selectedInstanceList.value.join(','),
      key: serachKey.value,
      record_ids: `${currentRecord.value.id}`,
    });
  };
</script>

<style lang="less">
  .hot-key-list-detail-header {
    display: flex;
    width: 100%;
    align-items: center;
    padding-right: 24px;

    .header-info {
      padding-left: 8px;
      font-size: 14px;
      color: #979ba5;
      border-left: 1px solid #dcdee5;
    }
  }

  .hot-key-list-detail-content {
    .filter-box {
      display: flex;
      padding: 16px 24px 0;
    }
  }
</style>
