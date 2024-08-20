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
  <TableTagInput
    ref="tagRef"
    :disabled="(checkExist || checkNotExist) && !clusterId"
    :model-value="localValue"
    :placeholder="t('请输入DB 名称，支持通配符“%”，含通配符的仅支持单个')"
    :rules="rules"
    :single="single"
    @change="handleChange" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { checkClusterDatabase } from '@services/source/dbbase';

  import TableTagInput from '@components/render-table/columns/db-table-name/Index.vue';

  interface Props {
    modelValue?: string[];
    initValue?: string[];
    clusterId?: number;
    required?: boolean;
    single?: boolean;
    checkExist?: boolean;
    allowAsterisk?: boolean;
    checkNotExist?: boolean;
    rules?: {
      validator: (value: string[]) => boolean;
      message: string;
    }[];
  }

  interface Emits {
    (e: 'change', value: string[]): void;
    (e: 'update:modelValue', value: string[]): void;
  }

  interface Exposes {
    getValue: (field: string) => Promise<Record<string, string[]>>;
  }

  const props = withDefaults(defineProps<Props>(), {
    modelValue: undefined,
    initValue: undefined,
    clusterId: undefined,
    required: true,
    single: false,
    checkExist: false,
    checkNotExist: false,
    rules: undefined,
    allowAsterisk: true,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const tagRef = ref();
  const localValue = ref(props.modelValue);

  const rules = computed(() => {
    if (props.rules && props.rules.length > 0) {
      return props.rules;
    }

    const systemDbNames = ['mysql', 'db_infobase', 'information_schema', 'performance_schema', 'sys', 'infodba_schema'];

    return [
      {
        validator: (value: string[]) => {
          if (!props.required) {
            return true;
          }
          return value && value.length > 0;
        },
        message: t('DB 名不能为空'),
      },
      {
        validator: (value: string[]) => _.every(value, (item) => /^(?!stage_truncate)(?!.*dba_rollback$).*/.test(item)),
        message: t('不能以stage_truncate开头或dba_rollback结尾'),
      },
      {
        validator: (value: string[]) => _.every(value, (item) => /^[-_a-zA-Z0-9*?%]{0,35}$/.test(item)),
        message: t('库表名支持数字、字母、中划线、下划线，最大35字符'),
      },
      {
        validator: (value: string[]) => _.every(value, (item) => !systemDbNames.includes(item)),
        message: t('不允许输入系统库和特殊库'),
      },
      {
        validator: (value: string[]) => {
          if (props.allowAsterisk) {
            return true;
          }

          return _.every(value, (item) => item !== '*');
        },
        message: t('不允许为 *'),
      },
      {
        validator: (value: string[]) =>
          !_.some(value, (item) => (/\*/.test(item) && item.length > 1) || (value.length > 1 && item === '*')),
        message: t('* 只能独立使用'),
      },
      {
        validator: (value: string[]) => _.every(value, (item) => !/^[%?]$/.test(item)),
        message: t('% 或 ? 不允许单独使用'),
      },
      {
        validator: (value: string[]) => {
          if (_.some(value, (item) => /[*%?]/.test(item))) {
            return value.length < 2;
          }
          return true;
        },
        message: t('含通配符的单元格仅支持输入单个对象'),
      },
      {
        validator: (value: string[]) => {
          if (!props.checkExist) {
            return true;
          }
          if (!props.clusterId) {
            return false;
          }
          // % 通配符不需要校验存在
          if (/%$/.test(value[0]) || value[0] === '*') {
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
        message: t('DB 已存在'),
      },
      {
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
        message: t('DB 不存在'),
      },
    ];
  });

  // 集群改变时 DB 需要重置
  watch(
    () => props.clusterId,
    () => {
      if (props.initValue) {
        localValue.value = props.initValue;
      } else {
        localValue.value = [];
      }
    },
  );

  watch(
    () => props.modelValue,
    () => {
      if (props.modelValue) {
        localValue.value = props.modelValue;
      } else {
        localValue.value = [];
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: string[]) => {
    localValue.value = value;
    emits('update:modelValue', value);
    emits('change', value);
  };

  defineExpose<Exposes>({
    getValue(field: string) {
      return tagRef.value
        .getValue()
        .then(() => {
          if (!localValue.value) {
            return Promise.reject();
          }
          return {
            [field]: props.single ? localValue.value[0] : localValue.value,
          };
        })
        .catch(() => Promise.reject({ [field]: props.single ? localValue.value?.[0] || '' : localValue.value }));
    },
  });
</script>
