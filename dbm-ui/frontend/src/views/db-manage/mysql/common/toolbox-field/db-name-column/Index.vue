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
  <DbNameColumn
    v-model="modelValue"
    :field="field"
    :label="label"
    :placeholder="t('请输入DB 名称，支持通配符“%”，含通配符的仅支持单个')"
    :required="required"
    :rules="localRules"
    :show-batch-edit="showBatchEdit"
    :single="single"
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
  </DbNameColumn>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { checkClusterDatabase } from '@services/source/dbbase';

  import DbNameColumn from '@views/db-manage/common/toolbox-field/column/db-table-name-column/Index.vue';

  interface Props {
    /**
     * @description 允许 * 独立使用
     * @default true
     */
    allowAsterisk?: boolean;
    /**
     * @description 允许通配符(%?*)
     * @default true
     */
    allowWildcard?: boolean;
    /**
     * @description DB 已存在报错
     * @default false
     */
    checkExist?: boolean;
    /**
     * @description DB 不存在报错
     * @default false
     */
    checkNotExist?: boolean;
    clusterId?: number;
    field: string;
    label: string;
    required?: boolean;
    rules?: NonNullable<ComponentProps<typeof DbNameColumn>['rules']>;
    showBatchEdit?: boolean;
    single?: boolean;
  }

  type Emits = (e: 'batch-edit', value: string[], field: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    allowAsterisk: true,
    allowWildcard: true,
    checkExist: false,
    checkNotExist: false,
    clusterId: undefined,
    disabled: false,
    required: false,
    rules: () => [],
    showBatchEdit: true,
    single: false,
  });
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  let isInit = true;

  const systemDbNames = ['mysql', 'db_infobase', 'information_schema', 'performance_schema', 'sys', 'infodba_schema'];

  const localRules = computed(() => [
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
      message: t('不允许输入系统库和特殊库 n', { n: systemDbNames.join(',') }),
      trigger: 'change',
      validator: (value: string[]) => _.every(value, (item) => !systemDbNames.includes(item)),
    },
    {
      message: t('不允许包含通配符'),
      trigger: 'change',
      validator: (value: string[]) => {
        if (props.allowWildcard) {
          return true;
        }
        return _.every(value, (item) => !/[*%?]/.test(item));
      },
    },
    {
      message: t('* 只能独立使用'),
      trigger: 'change',
      validator: (value: string[]) => !_.some(value, (item) => /\*/.test(item) && item.length > 1),
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
      message: t('% 不允许单独使用'),
      trigger: 'change',
      validator: (value: string[]) => _.every(value, (item) => !/^%$/.test(item)),
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
    {
      message: t('DB 已存在'),
      trigger: 'change',
      validator: (value: string[]) => {
        if (!props.checkExist) {
          return true;
        }
        // % 通配符不需要校验存在
        const clearDbList = _.filter(value, (item) => !/[*%?]/.test(item));
        if (clearDbList.length < 1) {
          return true;
        }
        if (!props.clusterId) {
          return false;
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
      trigger: 'change',
      validator: (value: string[]) => {
        if (!props.checkNotExist) {
          return true;
        }
        // % 通配符不需要校验存在
        const clearDbList = _.filter(value, (item) => !/[*%?]/.test(item));
        if (clearDbList.length < 1) {
          return true;
        }
        if (!props.clusterId) {
          return false;
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
    ...props.rules,
  ]);

  // 集群改变时 DB 需要重置
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
