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
  <div class="memory-analysis-instance-info mb-16">
    <div class="total-info">
      <span>
        {{ t('Key 数量：') }}
        <span class="info-item">{{ count }}</span>
      </span>
      ，
      <span>
        {{ t('内存占比：') }}
        <span class="info-item">{{ memoryUnsed }}%</span>
      </span>
      ，
      <span>
        {{ t('分析实例：') }}
        <span class="info-item">{{ instaceList.length }}</span>
        {{ t('个') }}
      </span>
      ，
      <span>
        <BkButton
          text
          theme="primary"
          @click="handleInstanceShow">
          {{ t('查看实例') }}
          <DbIcon
            class="ml-4"
            style="font-size: 16px"
            :type="showInstance ? 'up-big' : 'down-big'" />
        </BkButton>
      </span>
    </div>
    <div
      v-if="showInstance"
      class="instance-info mt-4">
      <div
        v-for="item in instaceList"
        :key="item"
        class="instance-item">
        {{ item }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    count: number;
    instaceList: string[];
    memoryUnsed: number;
  }

  type Emits = (e: 'change', value: boolean) => void;

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const showInstance = ref(false);

  const handleInstanceShow = () => {
    showInstance.value = !showInstance.value;
    emits('change', !showInstance.value);
  };
</script>

<style lang="less">
  .memory-analysis-instance-info {
    color: #313238;

    .total-info {
      height: 40px;
      padding: 0 16px;
      line-height: 40px;
      background-color: #f0f1f5;

      .info-item {
        font-weight: bolder;
      }
    }

    .instance-info {
      display: flex;
      max-height: 164px;
      padding: 12px 16px;
      overflow: scroll;
      background-color: #f0f1f5;
      flex-wrap: wrap;

      .instance-item {
        width: 132px;
        height: 20px;
        font-size: 12px;
        line-height: 20px;

        &:not(:last-child) {
          margin-right: 40px;
        }
      }
    }
  }
</style>
