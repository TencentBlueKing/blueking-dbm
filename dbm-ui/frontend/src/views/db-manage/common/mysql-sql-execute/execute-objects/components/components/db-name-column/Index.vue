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
    :append-rules="rules"
    :field="field"
    :label="label"
    :min-width="200"
    :required="required">
    <EditableTagInput
      v-model="modelValue"
      allow-auto-match
      allow-create
      clearable
      has-delete-icon
      :paste-fn="tagInputPasteFn"
      :placeholder="t('请输入DB 名称，支持通配符“%”，含通配符的仅支持单个')" />
    <template #tips>
      <div class="db-table-tag-tip">
        <div style="font-weight: 700">{{ t('库表输入说明') }}：</div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('不允许输入系统库和特殊库，如mysql、sys 等') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('DB名、表名不允许为空，忽略DB名、忽略表名不允许为 *') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('支持 %（指代任意长度字符串）, ?（指代单个字符串）, *（指代全部）三个通配符') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('单元格可同时输入多个对象，使用换行，空格或；，｜分隔，按 Enter 或失焦完成内容输入') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('% ? 不能独立使用， * 只能单独使用') }}</span>
        </div>
      </div>
    </template>
  </EditableColumn>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { batchSplitRegex } from '@common/regex';

  interface Props {
    field: string;
    label: string;
    required?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    required: false,
  });

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('DB 名不能为空'),
      trigger: 'change',
      validator: (value: string[]) => {
        if (!props.required) {
          return true;
        }

        return value && value.length > 0;
      },
    },
    {
      message: t('不能以stage_truncate开头或dba_rollback结尾'),
      trigger: 'change',
      validator: (value: string[]) => _.every(value, (item) => /^(?!stage_truncate)(?!.*dba_rollback$).*/.test(item)),
    },
    {
      message: t('库表名支持数字、字母、中划线、下划线，最大35字符'),
      trigger: 'change',
      validator: (value: string[]) => _.every(value, (item) => /^[-_a-zA-Z0-9*?%]{0,35}$/.test(item)),
    },
    {
      message: t('不允许输入系统库和特殊库'),
      trigger: 'change',
      validator: (value: string[]) =>
        _.every(
          value,
          (item) =>
            !['db_infobase', 'infodba_schema', 'information_schema', 'mysql', 'performance_schema', 'sys'].includes(
              item,
            ),
        ),
    },
    {
      message: t('* 只能独立使用'),
      trigger: 'change',
      validator: (value: string[]) =>
        !_.some(value, (item) => (/\*/.test(item) && item.length > 1) || (value.length > 1 && item === '*')),
    },
    {
      message: t('% 或 ? 不允许单独使用'),
      trigger: 'change',
      validator: (value: string[]) => _.every(value, (item) => !/^[%?]$/.test(item)),
    },
  ];

  const tagInputPasteFn = (value: string) => value.split(batchSplitRegex).map((item) => ({ id: item }));
</script>

<style lang="less" scoped>
  .db-table-tag-tip {
    display: flex;
    padding: 3px 7px;
    line-height: 24px;
    flex-direction: column;

    div {
      display: flex;
      align-items: center;

      .circle-dot {
        display: inline-block;
        width: 4px;
        height: 4px;
        margin-right: 6px;
        background-color: #63656e;
        border-radius: 50%;
      }
    }
  }
</style>
