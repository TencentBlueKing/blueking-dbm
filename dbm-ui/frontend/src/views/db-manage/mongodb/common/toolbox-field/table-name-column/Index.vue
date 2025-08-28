<template>
  <EditableColumn
    v-model="modelValue"
    :field="field"
    :label="label"
    :min-width="200"
    :required="required"
    :rules="rules">
    <template #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :single="single"
        :title="label"
        type="taginput"
        @change="handleBatchEdit">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-select-button"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <EditableTagInput
      v-model="modelValue"
      allow-auto-match
      allow-create
      clearable
      :disabled="disabled"
      has-delete-icon
      :max-data="single ? 1 : -1"
      :paste-fn="tagInputPasteFn"
      :placeholder="t('请输入表名，支持通配符“*”')"
      @change="handleChange" />
    <template #tips>
      <div class="mongo-table-name-tips">
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
  </EditableColumn>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { batchSplitRegex } from '@common/regex';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    // compareData?: string[];
    disabled?: boolean;
    field: string;
    label: string;
    required?: boolean;
    single?: boolean;
  }

  interface Emits {
    (e: 'batch-edit', value: string[], field: string): void;
    (e: 'change'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    compareData: undefined,
    disabled: false,
    required: true,
    single: false,
  });
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('表名长度不超过255个字符'),
      trigger: 'change',
      validator: (value: string[]) => _.every(value, (item) => item.length <= 255),
    },
    {
      message: t('输入格式有误'),
      trigger: 'change',
      validator: (value: string[]) => _.every(value, (item) => /^[a-zA-Z0-9_-]*\*?[a-zA-Z0-9_-]*$/.test(item)),
    },
    // {
    //   message: t('忽略DB名、忽略表名要么同时为空, 要么同时不为空'),
    //   trigger: 'change',
    //   validator: (value: string[]) => {
    //     const { compareData } = props;
    //     if (compareData) {
    //       return (value.length === 0 && compareData?.length === 0) || (value.length > 0 && compareData?.length > 0);
    //     }
    //     return true;
    //   },
    // },
  ];

  const isShowBatchEdit = ref(false);

  const tagInputPasteFn = (value: string) => value.split(batchSplitRegex).map((item) => ({ id: item }));

  const handleBatchEditShow = () => {
    isShowBatchEdit.value = true;
  };

  const handleBatchEdit = (value: string[] | string) => {
    emits('batch-edit', value as string[], props.field);
  };

  const handleChange = () => {
    emits('change');
  };
</script>

<style lang="less">
  .batch-select-button {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }

  .mongo-table-name-tips {
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
