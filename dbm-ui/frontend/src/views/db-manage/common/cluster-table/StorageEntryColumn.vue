<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <TableColumn
    class-name="cluster-table-storage-entry-column"
    col-key="storage_entry_display"
    :min-width="220"
    :title="t('存储入口')">
    <template #title>
      <RenderHeadCopy
        :config="[
          {
            field: 'storageEntryDisplay',
            label: t('域名'),
          },
        ]"
        :has-selected="selectedList.length > 0"
        :is-filter="isFilter"
        @handle-copy-all="handleCopyAllField"
        @handle-copy-selected="handleCopySelectedField">
        {{ t('存储入口') }}
      </RenderHeadCopy>
    </template>
    <template #default="{ row }: { row: { storageEntryDisplay: string } }">
      <TextOverflowLayout>
        <template v-if="row.storageEntryDisplay">
          <div
            v-for="node in row.storageEntryDisplay.split('\n')"
            :key="node">
            {{ node }}
          </div>
        </template>
        <span v-else>--</span>
        <template #append>
          <BkButton
            v-if="row.storageEntryDisplay"
            v-bk-tooltips="t('复制域名')"
            class="ml-4"
            role="table-cell-operation"
            text
            theme="primary"
            @click="handleCopy(row.storageEntryDisplay)">
            <DbIcon type="copy" />
          </BkButton>
        </template>
      </TextOverflowLayout>
    </template>
  </TableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useI18n } from 'vue-i18n';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';

  import { execCopy } from '@utils';

  import useColumnCopy from './hooks/useColumnCopy';
  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props<C extends ISupportClusterType> {
    // eslint-disable-next-line vue/no-unused-properties
    getTableInstance: () => any;
    isFilter: boolean;
    selectedList: ClusterModel<C>[];
  }

  const props = defineProps<Props<T>>();

  const { t } = useI18n();

  const { handleCopyAll, handleCopySelected } = useColumnCopy(props);

  // RenderHeadCopy 的 field 为本列字面量，收窄为宽签名避免与泛型 keyof 不兼容
  const handleCopyAllField = handleCopyAll as (field: string) => void;
  const handleCopySelectedField = handleCopySelected as (field: string) => void;

  const handleCopy = (data: string) => {
    execCopy(
      data,
      t('复制成功，共n条', {
        n: 1,
      }),
    );
  };
</script>
