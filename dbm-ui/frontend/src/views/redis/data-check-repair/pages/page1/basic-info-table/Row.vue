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
        :data="data.includeKey" />
    </td>
    <td
      style="padding: 0;">
      <RenderKeyRelated
        ref="excludeKeyRef"
        :data="data.excludeKey" />
    </td>
  </tr>
</template>
<script lang="ts">

  import RenderText from '@components/tools-table-common/RenderText.vue';

  import RenderInstance from './RenderInstance.vue';
  import RenderKeyRelated from './RenderKeyRelated.vue';

  export interface IDataRow {
    billId: number;
    relateTicket: number;
    srcCluster: string;
    instances: string;
    targetCluster: string;
    includeKey: string[];
    excludeKey: string[];
  }


  export type TableRealRowData = Pick<IDataRow, 'includeKey' | 'excludeKey' > & { instances: string[] };

</script>
<script setup lang="ts">
  import { listClusterList } from '@services/redis/toolbox';

  import { useGlobalBizs } from '@stores';

  interface Props {
    data: IDataRow,
  }

  interface Exposes {
    getValue: () => Promise<TableRealRowData>
  }

  const props = defineProps<Props>();

  const { currentBizId } = useGlobalBizs();
  const instanceRef = ref();
  const includeKeyRef = ref();
  const excludeKeyRef = ref();

  const instances = ref();

  watch(() => props.data.srcCluster, (domain) => {
    setTimeout(() => {
      queryInstances(domain);
    });
  }, {
    immediate: true,
  });

  const queryInstances = async (domain: string) => {
    const ret = await listClusterList(currentBizId, { domain });
    if (ret.length < 1) {
      return;
    }
    const data = ret[0];
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
          instances,
          includeKey,
          excludeKey,
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
