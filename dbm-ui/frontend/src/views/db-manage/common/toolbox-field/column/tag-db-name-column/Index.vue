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
  <Column
    :append-rules="rules"
    :field="field"
    :label="label"
    :min-width="minWidth"
    :required="required">
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
    <div
      ref="rootRef"
      style="flex: 1"
      @click="handleShowTips">
      <TagInput
        v-model="modelValue"
        allow-auto-match
        allow-create
        has-delete-icon
        :placeholder="t('请输入DB 名称，支持通配符“%”，含通配符的仅支持单个')" />
    </div>
  </Column>
  <div style="display: none">
    <div
      ref="popRef"
      style="font-size: 12px; line-height: 24px; color: #63656e">
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
    </div>
  </div>
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import { checkClusterDatabase } from '@services/source/dbbase';

  import { Column, TagInput } from '@components/editable-table/Index.vue';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    allowAsterisk?: boolean;
    checkExist?: boolean;
    checkNotExist?: boolean;
    clusterId: number;
    field: string;
    label: string;
    minWidth?: number;
    required?: boolean;
    rules?: {
      message: string;
      trigger: string;
      validator: (value: string[]) => boolean;
    }[];
  }

  type Emits = (e: 'batch-edit', value: string[], field: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    allowAsterisk: false,
    checkExist: false,
    checkNotExist: false,
    minWidth: 200,
    required: false,
    rules: () => [],
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  let tippyIns: Instance | undefined;

  const rootRef = ref();
  const popRef = ref();
  const showBatchEdit = ref(false);

  const rules = computed(() => {
    if (props.rules && props.rules.length > 0) {
      return props.rules;
    }

    const systemDbNames = ['mysql', 'db_infobase', 'information_schema', 'performance_schema', 'sys', 'infodba_schema'];

    return [
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
        message: t('不允许输入系统库和特殊库'),
        trigger: 'change',
        validator: (value: string[]) => _.every(value, (item) => !systemDbNames.includes(item)),
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
  });

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string[]) => {
    emits('batch-edit', value, props.field);
  };

  const handleShowTips = () => {
    tippyIns?.show();
  };

  onMounted(() => {
    nextTick(() => {
      if (rootRef.value) {
        tippyIns = tippy(rootRef.value as SingleTarget, {
          appendTo: () => document.body,
          arrow: true,
          content: popRef.value,
          hideOnClick: true,
          interactive: true,
          maxWidth: 'none',
          offset: [0, 18],
          placement: 'top',
          theme: 'light',
          trigger: 'manual',
          zIndex: 9998,
        });
      }
    });
  });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  });
</script>
<style lang="less" scoped>
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }

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
