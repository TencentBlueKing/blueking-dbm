<template>
  <Column
    :disabled-method="disabledMethod"
    field="tables"
    :label="label"
    :min-width="180"
    required
    :rules="rules">
    <EditTagInput
      v-model="modelValue"
      :placeholder="t('请输入表名称，支持通配符“%”，含通配符的仅支持单个')" />
    <template #tips>
      <div class="mysql-table-name-tips">
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
  </Column>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { Column, TagInput as EditTagInput } from '@components/editable-table/Index.vue';

  interface Props {
    label: string;
    clusterId?: number;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const disabledMethod = () => (props.clusterId ? false : t('请先选择集群'));

  const modelValue = defineModel<string[]>();

  const rules = [
    {
      validator: (value: string[]) => _.every(value, (item) => /^[-_a-zA-Z0-9*?%]{0,64}$/.test(item)),
      message: t('库表名支持数字、字母、中划线、下划线，最大64字符'),
      trigger: 'blur',
    },
    {
      validator: (value: string[]) => _.every(value, (item) => item !== '*'),
      message: t('不允许为 *'),
      trigger: 'blur',
    },
    {
      validator: (value: string[]) =>
        !_.some(value, (item) => (/\*/.test(item) && item.length > 1) || (value.length > 1 && item === '*')),
      message: t('* 只能独立使用'),
      trigger: 'blur',
    },
    {
      validator: (value: string[]) => _.every(value, (item) => !/^[%?]$/.test(item)),
      message: t('% 或 ? 不允许单独使用'),
      trigger: 'blur',
    },
  ];
</script>
<style lang="less">
  .mysql-table-name-tips {
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
