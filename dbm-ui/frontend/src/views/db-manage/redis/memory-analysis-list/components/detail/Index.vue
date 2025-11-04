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
      <div class="redis-memory-analysis-detail-header">
        <span>{{ t('内存分析报告') }}</span>
        <template v-if="currentRecord">
          <span class="header-info ml-8"> {{ currentRecord.root_id }}（{{ currentRecord.immute_domain }}） </span>
          <BkButton
            class="ml-8"
            :disabled="dataLength === 0"
            @click="handleExport">
            <DbIcon
              class="mr-4"
              type="daochu" />
            {{ t('导出') }}
          </BkButton>
        </template>
        <BkButton
          :key="currentIndex"
          v-bk-tooltips="currentIndex === 0 ? t('已经是第一条') : t('上一条')"
          :disabled="currentIndex === 0 || isLoading"
          style="width: 32px; margin-left: auto"
          @click="handleCurrentIndexChange(false)">
          <DbIcon type="up-big" />
        </BkButton>
        <BkButton
          :key="currentIndex"
          v-bk-tooltips="currentIndex === recordList.length - 1 ? t('已经是最后一条') : t('下一条')"
          class="ml-8"
          :disabled="currentIndex === recordList.length - 1 || isLoading"
          style="width: 32px"
          @click="handleCurrentIndexChange">
          <DbIcon type="down-big" />
        </BkButton>
      </div>
    </template>
    <template #default>
      <div class="redis-memory-analysis-detail-content">
        <BkRadioGroup
          v-model="tableType"
          class="mb-12"
          style="width: 100%"
          type="capsule">
          <BkRadioButton
            label="detail"
            style="width: 50%">
            {{ t('内存分析报告') }}
          </BkRadioButton>
          <BkRadioButton
            label="rank"
            style="width: 50%">
            {{ t('大 Key 排行榜') }}
          </BkRadioButton>
        </BkRadioGroup>
        <component
          :is="contentCom"
          :key="currentIndex"
          ref="contentRef"
          :instace-list="currentInstanceList"
          :record-id="currentRecord.record_id" />
      </div>
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import RedisKeystatAnalysisModel from '@services/model/redis/redis-keystat-analysis';
  import { exportKeystatAnalysis } from '@services/source/redisKeystat';

  import DetailContent from './components/detail/Index.vue';
  import RankContent from './components/rank/Index.vue';

  interface Props {
    recordList: RedisKeystatAnalysisModel[];
  }

  const props = defineProps<Props>();
  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });
  const currentIndex = defineModel<number>('currentIndex', {
    required: true,
  });

  const { t } = useI18n();

  const contentRef = ref<InstanceType<typeof DetailContent | typeof RankContent>>();
  const tableType = ref('detail');

  const contentCom = computed(() => {
    const contentMap = {
      detail: DetailContent,
      rank: RankContent,
    };
    return contentMap[tableType.value as keyof typeof contentMap];
  });

  const currentRecord = computed(() => props.recordList[currentIndex.value]);
  const currentInstanceList = computed(() => currentRecord.value.source_addr_list.map((item) => item.addr));
  const isLoading = computed(() => contentRef.value?.loading);
  const dataLength = computed(() => contentRef.value?.dataLength || 0);

  const handleCurrentIndexChange = (isNext = true) => {
    if (isNext) {
      currentIndex.value = currentIndex.value + 1;
    } else {
      currentIndex.value = currentIndex.value - 1;
    }
  };

  const handleExport = () => {
    exportKeystatAnalysis({
      record_ids: `${currentRecord.value.record_id}`,
    });
  };
</script>

<style lang="less">
  .redis-memory-analysis-detail-header {
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

  .redis-memory-analysis-detail-content {
    padding: 18px 24px;
  }
</style>
