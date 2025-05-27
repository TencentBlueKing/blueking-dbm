<template>
  <EditableColumn
    :disabled-method="disabledMethod"
    :field="field"
    :label="label"
    :min-width="180"
    :required="required"
    :rules="rules">
    <template #headAppend>
      <BatchEditColumn
        v-model="showBatchEdit"
        :title="label"
        type="taginput"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <EditableTagInput
      v-model="modelValue"
      :max-data="single ? 1 : -1"
      :placeholder="t('请输入DB 名称，支持通配符“%”，含通配符的仅支持单个')" />
    <template #tips>
      <div class="mysql-db-name-tips">
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

  import { checkClusterDatabase } from '@services/source/dbbase';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    allowAsterisk?: boolean;
    checkExist?: boolean;
    checkNotExist?: boolean;
    clusterId?: number;
    field: string;
    label: string;
    required?: boolean;
    single?: boolean;
  }

  type Emits = (e: 'batch-edit', value: string[], field: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    allowAsterisk: true,
    checkExist: false,
    checkNotExist: false,
    required: true,
    single: false,
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string[]>();

  const { t } = useI18n();

  const showBatchEdit = ref(false);

  const rules = [
    {
      message: t('不能以stage_truncate开头或dba_rollback结尾'),
      trigger: 'blur',
      validator: (value: string[]) => _.every(value, (item) => /^(?!stage_truncate)(?!.*dba_rollback$).*/.test(item)),
    },
    {
      message: t('库表名支持数字、字母、中划线、下划线，最大35字符'),
      trigger: 'blur',
      validator: (value: string[]) => _.every(value, (item) => /^[-_a-zA-Z0-9*?%]{0,35}$/.test(item)),
    },
    {
      message: t('不允许输入系统库和特殊库'),
      trigger: 'blur',
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
      message: t('不允许为 *'),
      trigger: 'blur',
      validator: (value: string[]) => {
        if (props.allowAsterisk) {
          return true;
        }

        return _.every(value, (item) => item !== '*');
      },
    },
    {
      message: t('* 只能独立使用'),
      trigger: 'blur',
      validator: (value: string[]) =>
        !_.some(value, (item) => (/\*/.test(item) && item.length > 1) || (value.length > 1 && item === '*')),
    },
    {
      message: t('% 或 ? 不允许单独使用'),
      trigger: 'blur',
      validator: (value: string[]) => _.every(value, (item) => !/^[%?]$/.test(item)),
    },
    {
      message: t('DB 已存在'),
      trigger: 'blur',
      validator: (value: string[]) => {
        if (!props.checkExist) {
          return true;
        }
        if (!props.clusterId) {
          return false;
        }
        // % 通配符不需要校验存在
        if (value[0].endsWith('%') || value[0] === '*') {
          return true;
        }
        const clearDbList = _.filter(value, (item) => !/[*%]/.test(item));
        if (clearDbList.length < 1) {
          return true;
        }
        return checkClusterDatabase({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_id: props.clusterId,
          db_list: value,
        }).then((data) => {
          const existDbList = Object.keys(data).reduce<string[]>((result, dbName) => {
            if (data[dbName]) {
              result.push(dbName);
            }
            return result;
          }, []);
          if (existDbList.length > 0) {
            return t('n 已存在', { n: existDbList.join('、') });
          }

          return true;
        });
      },
    },
    {
      message: t('DB 不存在'),
      trigger: 'blur',
      validator: (value: string[]) => {
        if (!props.checkNotExist) {
          return true;
        }
        if (!props.clusterId) {
          return false;
        }
        const clearDbList = _.filter(value, (item) => !/[*%]/.test(item));
        if (clearDbList.length < 1) {
          return true;
        }
        return checkClusterDatabase({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_id: props.clusterId,
          db_list: value,
        }).then((data) => {
          const notExistDbList = Object.keys(data).reduce<string[]>((result, dbName) => {
            if (!data[dbName]) {
              result.push(dbName);
            }
            return result;
          }, []);
          if (notExistDbList.length > 0) {
            return t('n 不存在', { n: notExistDbList.join('、') });
          }

          return true;
        });
      },
    },
  ];

  const disabledMethod = () => (props.clusterId ? false : t('请先选择集群'));

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string[] | string) => {
    emits('batch-edit', value as string[], props.field);
  };
</script>
<style lang="less">
  .mysql-db-name-tips {
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
