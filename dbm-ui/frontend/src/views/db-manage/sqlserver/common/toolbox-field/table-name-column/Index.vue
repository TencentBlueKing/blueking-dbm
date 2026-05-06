<template>
  <EditableColumn
    :disabled-method="localDisabledMethod"
    :field="field"
    :label="label"
    :min-width="180"
    :required="required"
    :rules="rules">
    <template
      v-if="showBatchEdit"
      #headAppend>
      <BatchEditColumn
        :confirm-handler="handleBatchEditConfirm"
        :label="label">
        <BatchEditTagInput v-model="batchEditValue" />
      </BatchEditColumn>
    </template>
    <EditableTagInput
      v-model="modelValue"
      :max-data="single ? 1 : -1"
      :placeholder="t('请输入表名称，支持通配符“%”，含通配符的仅支持单个')" />
    <template #tips>
      <div class="db-table-tag-tip">
        <div style="font-weight: 700">{{ t('库表输入说明') }}：</div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('不允许输入系统库，如"master", "msdb", "model", "tempdb", "Monitor"') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('DB名、表名不允许为空，忽略DB名、忽略表名不允许为 *') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('支持 %（指代任意长度字符串）,*（指代全部）2个通配符') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('单元格可同时输入多个对象，使用换行，空格或；，｜分隔，按 Enter 或失焦完成内容输入') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('包含通配符时, 每一单元格只允许输入单个对象。% 不能独立使用， * 只能单独使用') }}</span>
        </div>
      </div>
    </template>
  </EditableColumn>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { Column as EditableColumn } from '@components/editable-table/Index.vue';

  import BatchEditColumn, { BatchEditTagInput } from '@views/db-manage/common/batch-edit-column-new/Index.vue';

  interface Props {
    allowAsterisk?: boolean; // 是否允许单个 *
    clusterId?: number;
    // eslint-disable-next-line vue/require-default-prop
    disabledMethod?: ComponentProps<typeof EditableColumn>['disabledMethod'];
    field: string;
    label: string;
    required?: boolean;
    showBatchEdit?: boolean;
    single?: boolean;
  }

  type Emits = (e: 'batch-edit', value: string[], field: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    allowAsterisk: true,
    clusterId: undefined,
    disabled: false,
    required: true,
    showBatchEdit: true,
    single: false,
  });
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string[]>({
    default: () => [],
  });

  const { t } = useI18n();

  const batchEditValue = ref<string[]>([]);

  const rules = [
    {
      message: t('表名不能为空'),
      trigger: 'change',
      validator: (value: string[]) => {
        if (!props.required) {
          return true;
        }
        return value && value.length > 0;
      },
    },
    {
      message: t('库表名支持数字、字母、中划线、下划线，最大35字符'),
      trigger: 'change',
      validator: (value: string[]) => _.every(value, (item) => /^[-_a-zA-Z0-9*?%]{0,35}$/.test(item)),
    },
    {
      message: t('* 只能独立使用'),
      trigger: 'change',
      validator: (value: string[]) =>
        !_.some(value, (item) => (/\*/.test(item) && item.length > 1) || (value.length > 1 && item === '*')),
    },
    {
      message: t('不允许为 *'),
      trigger: 'change',
      validator: (value: string[]) => {
        if (props.allowAsterisk) {
          return true;
        }

        return _.every(value, (item) => item !== '*');
      },
    },
    {
      message: t('% 或 ? 不允许单独使用'),
      trigger: 'change',
      validator: (value: string[]) => _.every(value, (item) => !/^[%?]$/.test(item)),
    },
    {
      message: t('含通配符的单元格仅支持输入单个对象'),
      trigger: 'change',
      validator: (value: string[]) => {
        if (_.some(value, (item) => /[*%?]/.test(item))) {
          return value.length < 2;
        }
        return true;
      },
    },
    // TODO: 表不存在
  ];

  const localDisabledMethod = () => {
    if (props.disabledMethod) {
      return props.disabledMethod();
    }
    return props.clusterId ? false : t('请输入合法的集群域名');
  };

  const handleBatchEditConfirm = () => {
    emits('batch-edit', batchEditValue.value, props.field);
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
