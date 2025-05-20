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
    field="slave.spec_id"
    :label="t('新从库主机')"
    :min-width="150"
    required>
    <EditableSelect
      v-model="localValue"
      display-key="name"
      id-key="id"
      :list="optionList"
      :placeholder="t('请选择')">
      <template #option="{ item }">
        <div class="tendbcluster-restore-spec">
          {{ item.name }}
          <span class="spec-count">{{ count }}</span>
        </div>
      </template>
    </EditableSelect>
  </EditableColumn>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSpecResourceCount } from '@services/source/dbresourceResource';

  interface Props {
    slave: {
      bk_cloud_id: number;
      spec_id: number;
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const localValue = ref('resource_pool');
  const count = ref(0);

  const optionList = [
    {
      id: 'resource_pool',
      name: t('资源池自动匹配'),
      tooltips: t('当前为资源池自动匹配，切换类型将会清空并需重新选择'),
    },
  ];

  const { run: fetchSpecResourceCount } = useRequest(getSpecResourceCount, {
    manual: true,
    onSuccess(countResult) {
      count.value = countResult[props.slave.spec_id] ?? 0;
    },
  });

  watch(
    () => props.slave.spec_id,
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

<style lang="less">
  .tendbcluster-restore-spec {
    display: flex;
    width: 100%;
    flex: 1;
    align-items: center;
    justify-content: space-between;

    .spec-count {
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
