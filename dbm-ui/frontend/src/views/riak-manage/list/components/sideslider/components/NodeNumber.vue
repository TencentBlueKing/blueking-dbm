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
  <div class="node-number">
    <div class="node-number-current">
      <div>
        {{ t('当前节点总数') }} :
        <span class="node-number-current-total">{{ totalCount }}</span>
      </div>
      <div class="node-number-item">
        <DbIcon
          svg
          type="normal" />
        {{ t('正常') }} :
        <span class="node-number-current-normal">{{ normalCount }}</span>
      </div>
      <div class="node-number-item">
        <DbIcon
          svg
          type="abnormal" />
        {{ t('异常') }} :
        <span class="node-number-current-abnormal">{{ abnormalCount }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getRiakNodeList } from '@services/source/riak';

  import { useGlobalBizs } from '@stores';

  interface Props {
    id: number
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const totalCount = ref(0);
  const normalCount = ref(0);
  const abnormalCount = ref(0);

  useRequest(getRiakNodeList, {
    defaultParams: [{
      bk_biz_id: currentBizId,
      cluster_id: props.id,
    }],
    onSuccess(riakNodeListResult) {
      let normal = 0;
      let abnormal = 0;

      riakNodeListResult.results.forEach((riakNodeItem) => {
        if (riakNodeItem.isNodeNormal) {
          normal += 1;
        } else {
          abnormal += 1;
        }
      });

      totalCount.value = riakNodeListResult.results.length;
      normalCount.value = normal;
      abnormalCount.value = abnormal;
    },
  });
</script>

<style lang="less" scoped>
.node-number {
  .node-number-current {
    display: flex;
    padding: 16px 24px;
    margin: 24px 0 20px;
    background-color: @bg-gray;

    .node-number-item {
      display: flex;
      align-items: center;
      margin-left: 44px;
    }

    .node-number-current-total {
      display: inline-block;
      margin-left: 12px;
      font-weight: 700;
      color: @bg-default;
    }

    .node-number-current-normal {
      display: inline-block;
      margin-left: 12px;
      font-weight: 700;
      color: @success-color;
    }

    .node-number-current-abnormal {
      display: inline-block;
      margin-left: 12px;
      font-weight: 700;
      color: @danger-color;
    }
  }
}
</style>
