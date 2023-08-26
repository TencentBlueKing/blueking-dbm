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
  <tr>
    <td style="padding: 0;">
      <RenderSourceCluster
        ref="clusterRef"
        :data="data.srcCluster"
        :inputed="inputedClusters"
        @input-finish="handleInputFinish" />
    </td>
    <td
      style="padding: 0;">
      <RenderText
        :data="data.targetCluster"
        :is-loading="data.isLoading"
        :placeholder="$t('输入访问入口后自动生成')" />
    </td>
    <td
      style="padding: 0;">
      <RenderText
        :data="data.targetTime"
        :is-loading="data.isLoading"
        :placeholder="$t('输入访问入口后自动生成')" />
    </td>
    <td style="padding: 0;">
      <RenderKeyRelated
        ref="includeKeyRef"
        :data="data.includeKey"
        required />
    </td>
    <td
      style="padding: 0;">
      <RenderKeyRelated
        ref="excludeKeyRef"
        :data="data.excludeKey" />
    </td>
    <td :class="{'shadow-column': isFixed}">
      <div class="action-box">
        <div
          class="action-btn"
          @click="handleAppend">
          <DbIcon type="plus-fill" />
        </div>
        <div
          class="action-btn"
          :class="{
            disabled: removeable
          }"
          @click="handleRemove">
          <DbIcon type="minus-fill" />
        </div>
      </div>
    </td>
  </tr>
</template>
<script lang="ts">

  import RenderText from '@components/tools-table-common/RenderText.vue';

  import RenderKeyRelated from '@views/redis/common/edit-field/RegexKeys.vue';

  import { random } from '@utils';

  import RenderSourceCluster from './RenderSourceCluster.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    srcCluster: string;
    targetCluster: string;
    targetClusterId: number;
    targetTime: string;
    includeKey: string[];
    excludeKey: string[];
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    srcCluster: '',
    targetTime: '',
    targetCluster: '',
    targetClusterId: 0,
    includeKey: ['*'],
    excludeKey: [],
  });

  export interface InfoItem {
    src_cluster: string;
    dst_cluster: number;
    key_white_regex: string;
    key_black_regex: string;
    recovery_time_point: string;
  }

</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow,
    removeable: boolean,
    inputedClusters?: string[],
    isFixed?: boolean;
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void,
    (e: 'remove'): void,
    (e: 'clusterInputFinish', value: string): void
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>
  }

  const props = withDefaults(defineProps<Props>(), {
    inputedClusters: () => ([]),
    isFixed: false,
  });

  const emits = defineEmits<Emits>();

  const clusterRef = ref();
  const includeKeyRef = ref();
  const excludeKeyRef = ref();

  const handleInputFinish = (value: string) => {
    emits('clusterInputFinish', value);
  };

  const handleAppend = () => {
    emits('add', [createRowData()]);
  };

  const handleRemove = () => {
    if (props.removeable) {
      return;
    }
    emits('remove');
  };

  defineExpose<Exposes>({
    async getValue() {
      await clusterRef.value.getValue();
      return await Promise.all([
        includeKeyRef.value.getValue(),
        excludeKeyRef.value.getValue(),
      ]).then((data) => {
        const [
          includeKey,
          excludeKey,
        ] = data;
        return {
          src_cluster: props.data.srcCluster,
          dst_cluster: props.data.targetClusterId,
          key_white_regex: includeKey.join('\n'),
          key_black_regex: excludeKey.join('\n'),
          recovery_time_point: props.data.targetTime,
        };
      });
    },
  });

</script>
<style lang="less" scoped>
  .action-box {
    display: flex;
    align-items: center;

    .action-btn {
      display: flex;
      font-size: 14px;
      color: #c4c6cc;
      cursor: pointer;
      transition: all 0.15s;

      &:hover {
        color: #979ba5;
      }

      &.disabled {
        color: #dcdee5;
        cursor: not-allowed;
      }

      & ~ .action-btn {
        margin-left: 18px;
      }
    }
  }
</style>
