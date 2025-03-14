<template>
  <TableNameColumn
    v-model="modelValue"
    :disabled="disabled"
    :field="field"
    :label="label"
    :placeholder="t('请输入表名称，支持通配符“%”，含通配符的仅支持单个')"
    :required="required"
    :rules="rules"
    @batch-edit="handleBatchEdit"
    @change="handleChange">
    <template #tip>
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
  </TableNameColumn>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TableNameColumn from '@views/db-manage/common/toolbox-field/column/db-table-name-column/Index.vue';

  interface Props {
    allowAsterisk?: boolean; // 是否允许单个 *
    clusterId?: number;
    disabled?: boolean;
    field: string;
    label: string;
    required?: boolean;
  }

  type Emits = (e: 'batch-edit', value: string[], field: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    allowAsterisk: true,
    clusterId: undefined,
    disabled: false,
    required: true,
  });
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  let isInit = true;

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

  // 集群改变时表名需要重置
  watch(
    () => props.clusterId,
    () => {
      if (!isInit) {
        modelValue.value = [];
      }
    },
  );

  const handleBatchEdit = (value: string[]) => {
    isInit = false;
    emits('batch-edit', value, props.field);
  };

  const handleChange = () => {
    isInit = false;
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
