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
    field="db_patterns"
    :label="t('备份 DB')"
    :min-width="300"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :title="t('备份 DB')"
        type="taginput"
        @change="handleBatchEditChange">
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
      :disabled="(checkExist || checkNotExist) && !clusterId"
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

  import { checkClusterDatabase } from '@services/source/dbbase';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    allowAsterisk?: boolean;
    checkExist?: boolean;
    checkNotExist?: boolean;
    clusterId?: number;
  }

  type Emits = (e: 'batch-edit', value: string[], field: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    allowAsterisk: true,
    checkExist: false,
    checkNotExist: false,
    clusterId: undefined,
  });

  const emits = defineEmits<Emits>();
  const modelValue = defineModel<string[]>();

  const { t } = useI18n();

  const rules = [
    {
      message: t('DB 名不能为空'),
      trigger: 'change',
      validator: (value: string[]) => value.length > 0,
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
    {
      message: t('DB 已存在'),
      trigger: 'change',
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
      trigger: 'change',
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

  const isShowBatchEdit = ref(false);

  const handleBatchEditShow = () => {
    isShowBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string | string[]) => {
    emits('batch-edit', value as string[], 'db_patterns');
  };
</script>

<style lang="less" scoped>
  .batch-select-button {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
