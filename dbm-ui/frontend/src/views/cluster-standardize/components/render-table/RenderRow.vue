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
    <td style="padding: 0">
      <RenderDomain
        ref="domainRef"
        :data="data.domain"
        :inputed="inputed"
        @input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderText
        class="td-cell"
        :data="clusterTypeMap[data.clusterType]"
        :placeholder="t('自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderText
        class="td-cell"
        :data="data.bkBizName"
        :placeholder="t('自动生成')" />
    </td>
    <td style="padding: 0">
      <div
        v-if="data?.status"
        class="td-cell">
        <DbStatus :theme="statusMap[data.status].theme">{{ statusMap[data.status].text }}</DbStatus>
      </div>
      <RenderText
        v-else
        class="td-cell"
        :data="data.bkBizName"
        :placeholder="t('自动生成')" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import { useI18n } from 'vue-i18n';

  import DbStatus from '@components/db-status/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import { random } from '@utils';

  import RenderDomain from './RenderDomain.vue';

  export interface IDataRow {
    rowKey: string;
    id: number;
    domain: string;
    clusterName: string;
    clusterType: string;
    bkBizId: number;
    bkBizName: string;
    status: string;
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    id: 0,
    domain: '',
    clusterName: '',
    clusterType: '',
    bkBizId: 0,
    bkBizName: '',
    status: '',
  });
</script>

<script setup lang="ts">
  import TendbhaModel from '@services/model/mysql/tendbha';

  interface Props {
    data: IDataRow;
    removeable: boolean;
    inputed: string[];
  }

  interface Emits {
    (e: 'add'): void;
    (e: 'remove'): void;
    (e: 'inputClusterFinish', value: TendbhaModel): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const domainRef = ref<InstanceType<typeof RenderDomain>>();

  const clusterTypeMap: Record<string, string> = {
    tendbha: t('主从'),
    tendsingle: t('单节点'),
  };

  const statusMap: Record<string, { text: string; theme: string }> = {
    normal: {
      text: t('正常'),
      theme: 'success',
    },
    abnormal: {
      text: t('异常'),
      theme: 'danger',
    },
  };

  const handleInputFinish = (value: TendbhaModel) => {
    emits('inputClusterFinish', value);
  };

  const handleAppend = () => {
    emits('add');
  };

  const handleRemove = () => {
    if (props.removeable) {
      return;
    }
    emits('remove');
  };
</script>

<style lang="less" scoped>
  .td-cell {
    padding-left: 16px;
    background-color: #fff;
  }
</style>
