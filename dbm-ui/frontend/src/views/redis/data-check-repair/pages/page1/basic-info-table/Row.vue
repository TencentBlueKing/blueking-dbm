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
    <td class="ticket-column">
      {{ data.relateTicket }}
    </td>
    <td style="padding: 0;">
      <RenderText
        :data="data.srcCluster" />
    </td>
    <td style="padding: 0;">
      <RenderInstance
        ref="instanceRef"
        :data="data.instances"
        :select-list="instances" />
    </td>
    <td
      style="padding: 0;">
      <RenderText
        :data="data.targetCluster" />
    </td>
    <td style="padding: 0;">
      <RenderKeyRelated
        ref="includeKeyRef"
        :data="data.includeKey"
        :required="isIncludeKeyRequired"
        @change="handleIncludeKeysChange" />
    </td>
    <td
      style="padding: 0;">
      <RenderKeyRelated
        ref="excludeKeyRef"
        :data="data.excludeKey"
        :required="isExcludeKeyRequired"
        @change="handleExcludeKeysChange" />
    </td>
  </tr>
</template>
<script lang="ts">

  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderKeyRelated from '@views/redis/common/edit-field/RegexKeys.vue';

  import RenderInstance from './RenderInstance.vue';

  export interface IDataRow {
    billId: number;
    relateTicket: number;
    srcCluster: string;
    instances: string;
    targetCluster: string;
    includeKey: string[];
    excludeKey: string[];
  }

  export interface InfoItem {
    bill_id: number; // 关联的(数据复制)单据ID
    src_cluster: string; // 源集群,来自于数据复制记录
    src_instances: string[]; // 源实例列表
    dst_cluster: string; // 目的集群,来自于数据复制记录
    key_white_regex: string;// 包含key
    key_black_regex:string;// 排除key
  }

</script>
<script setup lang="ts">
  import { getRedisList } from '@services/source/redis';

  interface Props {
    data: IDataRow,
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>
  }

  const props = defineProps<Props>();

  const instanceRef = ref();
  const includeKeyRef = ref();
  const excludeKeyRef = ref();

  const instances = ref();
  const isIncludeKeyRequired = ref(false);
  const isExcludeKeyRequired = ref(false);

  watch(() => props.data.srcCluster, (domain) => {
    setTimeout(() => {
      queryInstances(domain);
    });
  }, {
    immediate: true,
  });

  const handleIncludeKeysChange = (arr: string[]) => {
    isExcludeKeyRequired.value = arr.length === 0;
  };

  const handleExcludeKeysChange = (arr: string[]) => {
    isIncludeKeyRequired.value = arr.length === 0;
  };

  const queryInstances = async (domain: string) => {
    const [cluster] = domain.split(':');
    const result = await getRedisList({ domain: cluster });
    if (result.results.length < 1) {
      return;
    }
    const data = result.results[0];
    instances.value = data.redis_master.map(row => `${row.ip}:${row.port}`);
  };

  defineExpose<Exposes>({
    async getValue() {
      return await Promise.all([
        instanceRef.value.getValue(),
        includeKeyRef.value.getValue(),
        excludeKeyRef.value.getValue(),
      ]).then((data) => {
        const [
          instances,
          includeKey,
          excludeKey,
        ] = data;
        return {
          bill_id: props.data.billId,
          src_cluster: props.data.srcCluster,
          src_instances: instances,
          dst_cluster: props.data.targetCluster,
          key_white_regex: includeKey.join('\n'),
          key_black_regex: excludeKey.join('\n'),
        };
      });
    },
  });

</script>
<style lang="less" scoped>
.ticket-column {
  width: 100%;
  padding: 10px 16px;
  overflow: hidden;
  line-height: 20px;
  color: #3A84FF;
  text-overflow: ellipsis;
  white-space: nowrap;
}

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
