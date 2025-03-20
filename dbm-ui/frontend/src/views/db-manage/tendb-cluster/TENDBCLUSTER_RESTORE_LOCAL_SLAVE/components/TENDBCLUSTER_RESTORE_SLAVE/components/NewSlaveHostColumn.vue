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
  <EditableColumn
    field="newSlave"
    :label="t('新从库主机')"
    :min-width="150"
    required>
    <div class="table-cell">
      <TableEditSelect
        v-model="modelValue"
        :disabled="!slave.spec_id"
        :input-search="false"
        :list="optionList"
        :placeholder="t('请选择')">
        <template #option="{ optionItem }">
          <div class="spec-display">
            {{ optionItem.name }}
            <span class="spec-display-count">{{ countMap[optionItem.id] }}</span>
          </div>
        </template>
      </TableEditSelect>
    </div>
  </EditableColumn>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSpecResourceCount } from '@services/source/dbresourceResource';

  import TableEditSelect from '@views/db-manage/tendb-cluster/common/edit/SelectInput.vue';

  interface Props {
    slave: {
      bk_cloud_id: number;
      spec_id: number;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>();

  const { t } = useI18n();

  const optionList = [
    {
      id: 'resource_pool',
      name: t('资源池自动匹配'),
      tooltips: t('当前为资源池自动匹配，切换类型将会清空并需重新选择'),
    },
  ];

  const countMap = reactive<Record<string, number>>({
    resource_pool: 0,
    // resource_pool_manual: 0,
    // manual_input: 0,
  });

  const { run: fetchSpecResourceCount } = useRequest(getSpecResourceCount, {
    manual: true,
    onSuccess(countResult) {
      countMap.resource_pool = countResult[props.slave.spec_id] ?? 0;
    },
  });

  watch(
    () => props.slave,
    () => {
      if (props.slave.spec_id) {
        fetchSpecResourceCount({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: props.slave.bk_cloud_id,
          spec_ids: [props.slave.spec_id],
        });
      }
    },
  );
</script>

<style lang="less" scoped>
  .table-cell {
    flex: 1;
    padding: 1px;
  }
</style>

<style lang="less">
  .spec-display {
    display: flex;
    width: 100%;
    flex: 1;
    align-items: center;
    justify-content: space-between;

    .spec-display-count {
      height: 16px;
      min-width: 20px;
      font-size: 12px;
      line-height: 16px;
      color: #979ba5;
      text-align: center;
      background-color: #f0f1f5;
      border-radius: 2px;
    }
  }
</style>
