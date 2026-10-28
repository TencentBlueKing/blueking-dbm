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
  <BkSideslider
    v-model:is-show="isShow"
    quick-close
    render-directive="if"
    :width="960"
    @closed="emit('close')">
    <template #header>
      <div class="param-runtime-detail-header">
        <span class="param-runtime-detail-title">{{ t('运行值明细') }}</span>
        <div class="param-runtime-detail-sub-title">
          <span class="param-runtime-detail-label">{{ t('参数名') }}:</span>
          <TextOverflowLayout class="param-runtime-detail-value">
            {{ parameter.conf_name }}
          </TextOverflowLayout>
          <span class="param-runtime-detail-label">{{ t('设定值') }}:</span>
          <TextOverflowLayout class="param-runtime-detail-value">
            {{ parameter.flag_encrypt === 1 ? '******' : (parameter.conf_value ?? '--') }}
          </TextOverflowLayout>
          <span class="param-runtime-detail-label">{{ t('最近获取') }}:</span>
          <span class="param-runtime-detail-time">
            {{ runtime?.fetchedAt ? utcDisplayTime(runtime.fetchedAt) : '--' }}
          </span>
        </div>
      </div>
    </template>
    <div class="param-runtime-detail-content">
      <PrimaryTable
        :data="instances"
        row-key="address">
        <TableColumn
          col-key="address"
          ellipsis
          :min-width="200"
          :title="t('实例')" />
        <TableColumn
          col-key="role"
          ellipsis
          :min-width="140"
          :title="t('角色')" />
        <TableColumn
          col-key="value"
          :min-width="140"
          :title="t('运行值')">
          <template #default="{ row }: { row: RuntimeInstance }">
            <TextOverflowLayout>
              {{ row.value === null ? '--' : parameter.flag_encrypt === 1 ? '******' : row.value }}
            </TextOverflowLayout>
          </template>
        </TableColumn>
        <TableColumn
          col-key="comparison"
          :min-width="100"
          :title="t('对比结果')">
          <template #default="{ row }: { row: RuntimeInstance }">
            <span :class="{ 'param-runtime-detail-inconsistent': row.comparison === 'inconsistent' }">
              {{ comparisonLabels[row.comparison] }}
            </span>
          </template>
        </TableColumn>
        <TableColumn
          col-key="fetchedAt"
          :min-width="180"
          :title="t('最近获取时间')">
          <template #default="{ row }: { row: RuntimeInstance }">
            {{ row.fetchedAt ? utcDisplayTime(row.fetchedAt) : '--' }}
          </template>
        </TableColumn>
      </PrimaryTable>
    </div>
  </BkSideslider>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { ParameterConfigItem } from '@services/source/configs';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import type {
    RuntimeComparison,
    RuntimeConfig,
    RuntimeInstance,
  } from '@views/db-configure/components/runtime-config';

  import { utcDisplayTime } from '@utils';

  interface Props {
    parameter: ParameterConfigItem;
    runtime?: RuntimeConfig;
  }

  type Emits = (e: 'close') => void;

  const props = withDefaults(defineProps<Props>(), { runtime: undefined });

  const emit = defineEmits<Emits>();

  const { t } = useI18n();
  const isShow = ref(true);

  const comparisonLabels: Record<RuntimeComparison, string> = {
    consistent: t('一致'),
    inconsistent: t('不一致'),
    unknown: t('无法判断'),
  };
  const instances = computed(() =>
    [...(props.runtime?.instances ?? [])].sort((left, right) => {
      const priority = (item: RuntimeInstance) => item.comparison === 'inconsistent' || item.value === null;
      return Number(priority(right)) - Number(priority(left));
    }),
  );
</script>

<style lang="less" scoped>
  .param-runtime-detail-header {
    display: flex;
    width: 100%;
    min-width: 0;
    align-items: center;
  }

  .param-runtime-detail-title {
    flex-shrink: 0;
  }

  .param-runtime-detail-sub-title {
    position: relative;
    display: flex;
    min-width: 0;
    height: 22px;
    padding-left: 9px;
    margin-left: 16px;
    font-size: 14px;
    line-height: 22px;
    color: #979ba5;
    white-space: nowrap;
    align-items: center;
    flex: 1;

    &::before {
      position: absolute;
      top: 4px;
      left: 0;
      width: 1px;
      height: 14px;
      background-color: #979ba580;
      content: '';
    }
  }

  .param-runtime-detail-label {
    margin-right: 8px;
    flex-shrink: 0;
  }

  .param-runtime-detail-value {
    min-width: 0;
    margin-right: 20px;
    flex: 0 1 auto;
  }

  .param-runtime-detail-time {
    flex-shrink: 0;
  }

  .param-runtime-detail-content {
    padding: 20px 24px;
    font-size: 12px;
    color: #63656e;
  }

  .param-runtime-detail-inconsistent {
    color: #ff9c01;
  }
</style>
