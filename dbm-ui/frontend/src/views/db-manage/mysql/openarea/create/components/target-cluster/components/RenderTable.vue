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
  <RenderTable>
    <template #default>
      <RenderTableHeadColumn
        :min-width="120"
        :width="200">
        {{ t('目标集群') }}
        <template #append>
          <BatchOperateIcon
            class="ml-4"
            @click="handleShowBatchSelector" />
        </template>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        v-for="variableName in variableList"
        :key="variableName"
        :min-width="170"
        :width="180">
        {{ variableName }}
        <template #append>
          <BatchEditColumn
            v-model="showBatchEdit[variableName]"
            :placeholder="t('只能包含英文字母、数字，多个换行分隔')"
            :title="variableName"
            type="textarea"
            @change="(value: string) => handleBatchEdit(value, variableName)">
            <BatchOperateIcon
              class="ml-4"
              type="entry"
              @click="() => handleShowBatchEdit(variableName)" />
          </BatchEditColumn>
        </template>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        v-if="showIpCloumn"
        :min-width="100"
        :required="false"
        :width="190">
        {{ t('授权 IP') }}
        <template #append>
          <BatchOperateIcon
            class="ml-4"
            type="edit"
            @click="handleShowBatchChangeIp" />
        </template>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        fixed="right"
        :required="false"
        :width="100">
        {{ t('操作') }}
      </RenderTableHeadColumn>
    </template>

    <template #data>
      <slot />
    </template>
  </RenderTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';
  import BatchOperateIcon from '@views/db-manage/common/batch-operate-icon/Index.vue';

  interface Props {
    variableList: string[];
    showIpCloumn: boolean;
  }

  interface Emits {
    (e: 'batchSelectCluster'): void;
    (e: 'batchIpSelecter'): void;
    (e: 'batchEdit', varName: string, value: string[]): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const initShowBatchEdit = () =>
    props.variableList.reduce(
      (results, varName) => {
        Object.assign(results, { [varName]: false });
        return results;
      },
      {} as Record<string, boolean>,
    );

  const { t } = useI18n();

  const showBatchEdit = reactive(initShowBatchEdit());

  const handleShowBatchEdit = (key: string) => {
    showBatchEdit[key] = !showBatchEdit[key];
  };

  const handleBatchEdit = (value: string, varName: string) => {
    const list = value.trim().split('\n');
    emits('batchEdit', varName, list);
  };

  const handleShowBatchSelector = () => {
    emits('batchSelectCluster');
  };

  const handleShowBatchChangeIp = () => {
    emits('batchIpSelecter');
  };
</script>
