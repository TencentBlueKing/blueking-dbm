<template>
  <TableNameColumn
    v-model="modelValue"
    :disabled="disabled"
    :field="field"
    :label="label"
    :placeholder="t('请输入DB 名称，支持通配符“*”')"
    :required="required"
    :rules="rules"
    @batch-edit="handleBatchEdit">
    <template #tip>
      <div class="db-table-tag-tip">
        <div style="font-weight: 700">{{ t('库表输入说明') }}：</div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('不允许输入系统库和特殊库，如admin、config、local') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('DB名、表名不允许为空，忽略DB名、忽略表名要么同时为空, 要么同时不为空') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('支持通配符 *（指代任意长度字符串）') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('单元格可同时输入多个对象，使用换行，空格或；，｜分隔，按 Enter 或失焦完成内容输入') }}</span>
        </div>
      </div>
    </template>
  </TableNameColumn>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TableNameColumn from '@views/db-manage/common/toolbox-field/column/db-table-name-column/Index.vue';

  interface Props {
    label: string;
    field: string;
    required?: boolean;
    disabled?: boolean;
    compareData?: string[];
  }

  interface Emits {
    (e: 'batch-edit', value: string[], field: string): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    required: true,
    disabled: false,
    compareData: undefined,
  });
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      validator: (value: string[]) => _.every(value, (item) => item.length <= 64),
      trigger: 'change',
      message: t('库名长度不超过64个字符'),
    },
    {
      validator: (value: string[]) => _.every(value, (item) => /^[a-zA-Z0-9_-]*\*?[a-zA-Z0-9_-]*$/.test(item)),
      trigger: 'change',
      message: t('输入格式有误'),
    },
    {
      validator: (value: string[]) => _.every(value, (item) => !['admin', 'config', 'local'].includes(item)),
      trigger: 'change',
      message: t('不允许输入系统库和特殊库'),
    },
    {
      validator: (value: string[]) => {
        const { compareData } = props;
        if (compareData) {
          return (value.length === 0 && compareData?.length === 0) || (value.length > 0 && compareData?.length > 0);
        }
        return true;
      },
      message: t('忽略DB名、忽略表名要么同时为空, 要么同时不为空'),
      trigger: 'change',
    },
  ];

  const handleBatchEdit = (value: string[]) => {
    emits('batch-edit', value, props.field);
  };
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
