<template>
  <Column
    :disabled-method="disabledMethod"
    field="databases"
    :label="t('目标 DB')"
    :min-width="180"
    required
    :rules="rules">
    <EditTagInput
      v-model="modelValue"
      :placeholder="t('请输入DB 名称，支持通配符“%”，含通配符的仅支持单个')" />
  </Column>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { checkClusterDatabase } from '@services/source/dbbase';

  import { Column, TagInput as EditTagInput } from '@components/editable-table/Index.vue';

  interface Props {
    clusterId?: number;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const disabledMethod = () => (props.clusterId ? false : t('请先选择集群'));

  const modelValue = defineModel<string[]>();

  const systemDbNames = ['mysql', 'db_infobase', 'information_schema', 'performance_schema', 'sys', 'infodba_schema'];

  const rules = [
    {
      validator: (value: string[]) => _.every(value, (item) => /^(?!stage_truncate)(?!.*dba_rollback$).*/.test(item)),
      message: t('不能以stage_truncate开头或dba_rollback结尾'),
      trigger: 'blur',
    },
    {
      validator: (value: string[]) => _.every(value, (item) => /^[-_a-zA-Z0-9*?%]{0,35}$/.test(item)),
      message: t('库表名支持数字、字母、中划线、下划线，最大35字符'),
      trigger: 'blur',
    },
    {
      validator: (value: string[]) => _.every(value, (item) => !systemDbNames.includes(item)),
      message: t('不允许输入系统库和特殊库'),
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
    {
      validator: (value: string[]) => {
        const clearDbList = _.filter(value, (item) => !/[*%]/.test(item));
        if (clearDbList.length < 1) {
          return true;
        }
        return checkClusterDatabase({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_id: props.clusterId as number,
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
      message: t('DB 不存在'),
      trigger: 'blur',
    },
  ];
</script>
