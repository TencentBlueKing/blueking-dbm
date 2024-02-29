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
  <BkLoading :loading="isLoading">
    <div
      ref="textRef"
      v-bk-tooltips="{
        content: placeholder,
        disabled: !isOverflow,
      }"
      class="capacity-box"
      :class="{ 'default-display': !data }">
      <span
        v-if="!data"
        style="color: #c4c6cc">
        {{ placeholder }}
      </span>
      <div
        v-else
        class="content">
        <!-- <span style="margin-right: 5px;">{{ $t('磁盘') }}:</span>
        <BkProgress
          color="#EA3636"
          :percent="percent"
          :show-text="false"
          size="small"
          :stroke-width="18"
          type="circle"
          :width="20" />
        <span class="percent">{{ percent }}%</span> -->
        <!-- <span class="spec">{{ `(${data.used}G/${data.total}G)` }}</span> -->
        <span class="spec">{{ `${data.total}G` }}</span>
      </div>
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useIsWidthOverflow } from '@hooks';

  import type { IDataRow } from './Row.vue';

  interface Props {
    data?: IDataRow['currentCapacity'];
    isLoading?: boolean;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const textRef = ref();

  const renderData = computed(() => props.data);

  const placeholder = t('选择集群后自动生成');

  const { isOverflow } = useIsWidthOverflow(textRef, renderData);
  // const percent = computed(() => {
  //   if (props.data) return Number(((props.data.used / props.data.total) * 100).toFixed(2));
  //   return 0;
  // });
</script>
<style lang="less" scoped>
  .capacity-box {
    padding: 11px 16px;
    overflow: hidden;
    line-height: 20px;
    color: #63656e;
    text-overflow: ellipsis;
    white-space: nowrap;

    .content {
      display: flex;
      align-items: center;

      .percent {
        margin-left: 4px;
        font-size: 12px;
        font-weight: bold;
        color: #313238;
      }

      .spec {
        margin-left: 2px;
        font-size: 12px;
        // color: #979BA5;
      }
    }
  }

  .default-display {
    cursor: not-allowed;
    background: #fafbfd;
  }
</style>
