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
    field="targetSpec"
    :label="t('目标规格')"
    :min-width="280"
    readonly
    :rowspan="rowspan">
    <EditableBlock>
      <template v-if="specs.length > 0">
        <div
          v-for="item in specs"
          :key="item.role"
          class="target-spec-item">
          <div class="target-spec-main">{{ item.role }}: {{ item.specName || '-' }} × {{ item.count }}</div>
          <div
            v-if="item.sourceSpecs && item.sourceSpecs.length > 0"
            class="target-spec-aux">
            {{ t('源') }}: {{ item.sourceSpecs.map((source) => `${source.name} × ${source.count}`).join(', ') }}
          </div>
        </div>
      </template>
      <span v-else>-</span>
    </EditableBlock>
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { TargetSpecItem } from './types';

  interface Props {
    rowspan?: number;
    /** 只读派生的目标规格，按角色顺序由上至下展示 */
    specs: TargetSpecItem[];
  }

  withDefaults(defineProps<Props>(), {
    rowspan: 1,
  });

  const { t } = useI18n();
</script>
<style lang="less" scoped>
  .target-spec-main {
    line-height: 20px;
    color: #313238;
  }

  .target-spec-aux {
    line-height: 20px;
    color: #979ba5;
  }
</style>
