<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkSideslider
    :before-close="handleBeforeClose"
    class="config-edit-diff-sideslider"
    :is-show="isShow"
    quick-close
    render-directive="if"
    width="60%"
    @closed="handleClose">
    <template #header>
      {{ t('批量编辑参数') }}
      <span class="batch-edit-subtitle">
        {{ fetchParams.version || '' }}
      </span>
      <span class="batch-edit-count ml-40">
        {{ t('已选 : n 个参数', { n: editItems.length }) }}
      </span>
    </template>

    <!-- 步骤指示器 -->
    <div class="batch-edit-steps">
      <div class="step-item">
        <span
          class="step-circle"
          :class="currentStep > 1 ? 'is-done' : 'is-active'">
          <DbIcon
            v-if="currentStep > 1"
            type="bk-dbm-icon db-icon-check-line" />
          <span v-else>1</span>
        </span>
        <span class="step-label">{{ t('参数配置') }}</span>
      </div>
      <span class="step-line" />
      <div class="step-item">
        <span
          class="step-circle"
          :class="currentStep === 2 ? 'is-active' : 'is-pending'">
          2
        </span>
        <span class="step-label">{{ t('差异对比') }}</span>
      </div>
    </div>

    <div class="batch-edit-body">
      <DbCard class="batch-edit-card">
        <BkAlert
          class="mb-16"
          theme="warning"
          :title="t('批量编辑后_参数配置将转为自定义状态_且不再随父级更新')" />

        <!-- Step 1: 编辑表格 -->
        <PrimaryTable
          v-if="currentStep === 1"
          :data="filteredEditItems"
          :filter-value="filterValue"
          :max-height="TABLE_MAX_HEIGHT"
          resizable
          row-key="conf_name"
          @filter-change="handleFilterChange">
          <TableColumn
            col-key="conf_name"
            ellipsis
            :title="t('参数名')"
            :width="240" />
          <TableColumn
            col-key="conf_value"
            :title="t('当前值')"
            :width="260">
            <template #default="{ row }">
              <ValueEditor
                v-model="row.conf_value"
                :is-encrypted="row.flag_encrypt === 1"
                :value-allowed="row.value_allowed || ''"
                :value-type-sub="row.value_type_sub || ''" />
            </template>
          </TableColumn>
          <TableColumn
            col-key="value_allowed"
            ellipsis
            :title="t('允许值')"
            :width="300">
            <template #default="{ row }">
              <template v-if="row.value_type_sub && row.value_type_sub !== 'STRING'">
                <BkTag>{{ row.value_type_sub }}</BkTag>
                <span class="ml-4">{{ row.value_allowed || '--' }}</span>
              </template>
              <span
                v-else
                class="no-constraint-text">
                {{ t('无约束') }}
              </span>
            </template>
          </TableColumn>
          <TableColumn
            col-key="need_restart"
            :filter="needRestartFilter"
            :title="t('重启生效')"
            :width="120">
            <template #default="{ row }">
              {{ row.need_restart === 1 ? t('是') : t('否') }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="row-operation"
            fixed="right"
            :title="t('操作')"
            :width="80">
            <template #default="{ rowIndex }">
              <BkButton
                text
                theme="primary"
                @click="handleRemoveItem(rowIndex)">
                {{ t('移除') }}
              </BkButton>
            </template>
          </TableColumn>
        </PrimaryTable>

        <!-- Step 2: 差异对比 -->
        <div
          v-if="currentStep === 2"
          class="diff-table-scroll">
          <table class="diff-table">
            <thead>
              <tr>
                <th>{{ t('参数名') }}</th>
                <th>{{ t('修改前') }}</th>
                <th>{{ t('修改后') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item of diffItems"
                :key="item.conf_name">
                <td>
                  <span
                    v-bk-tooltips="{
                      content: item.conf_name,
                      disabled: !overflowMap[item.conf_name],
                    }"
                    class="diff-cell-text"
                    @mouseenter="(e: MouseEvent) => checkOverflow(e, item.conf_name)">
                    {{ item.conf_name }}
                  </span>
                </td>
                <td>
                  <span
                    v-bk-tooltips="{
                      content: item.originValue,
                      disabled: !overflowMap[`origin_${item.conf_name}`],
                    }"
                    class="diff-cell-text"
                    @mouseenter="(e: MouseEvent) => checkOverflow(e, `origin_${item.conf_name}`)">
                    {{ item.originValue }}
                  </span>
                </td>
                <td :class="{ 'is-changed': item.isChanged }">
                  <span
                    v-bk-tooltips="{
                      content: item.newValue,
                      disabled: !overflowMap[`new_${item.conf_name}`],
                    }"
                    class="diff-cell-text"
                    @mouseenter="(e: MouseEvent) => checkOverflow(e, `new_${item.conf_name}`)">
                    {{ item.newValue }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </DbCard>
    </div>

    <template #footer>
      <template v-if="currentStep === 1">
        <BkButton
          class="mr-8"
          theme="primary"
          @click="handleNextStep">
          {{ t('下一步：差异对比') }}
        </BkButton>
        <BkButton @click="handleClose">
          {{ t('取消') }}
        </BkButton>
      </template>
      <template v-else>
        <BkButton
          class="mr-8"
          @click="handlePrevStep">
          {{ t('上一步') }}
        </BkButton>
        <BkButton
          class="mr-8"
          :loading="submitLoading"
          theme="primary"
          @click="handleSave">
          {{ t('保存') }}
        </BkButton>
        <BkButton @click="handleClose">
          {{ t('取消') }}
        </BkButton>
      </template>
    </template>
  </BkSideslider>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { updateBusinessConfig, validateConfItems } from '@services/source/configs';

  import { useBeforeClose } from '@hooks';

  import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';
  import { PrimaryTable } from '@components/tdesign-ui/table';

  import { messageSuccess } from '@utils';

  import type { ConfItem } from './ParamTable.vue';
  import ValueEditor from './ValueEditor.vue';

  interface Props {
    data: ConfItem[];
    /** 提交参数 */
    fetchParams: Record<string, any>;
  }

  const props = defineProps<Props>();

  const emit = defineEmits<{
    (e: 'saved'): void;
    (e: 'close'): void;
  }>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const currentStep = ref(1);
  const submitLoading = ref(false);
  const editItems = ref<ConfItem[]>([]);
  const originItems = ref<ConfItem[]>([]);
  const filterValue = ref<Record<string, string>>({});
  const overflowMap = ref<Record<string, boolean>>({});

  // 表格最大高度：视口 - header(44) - steps(48) - alert(~40) - body padding(32) - card padding(32) - footer(52)
  const TABLE_MAX_HEIGHT = `${window.innerHeight - 248}px`;

  /** 检测文本是否溢出 */
  const checkOverflow = (e: MouseEvent, key: string) => {
    const target = e.target as HTMLElement;
    overflowMap.value[key] = target.scrollWidth > target.clientWidth;
  };

  // 根据筛选条件过滤后的数据
  const filteredEditItems = computed(() => {
    let data = [...editItems.value];
    const filters = filterValue.value;

    // 列筛选过滤
    if (Object.keys(filters).length > 0) {
      data = data.filter((item) =>
        Object.entries(filters).every(([key, val]) => {
          if (!val) return true;
          if (key === 'need_restart') {
            // need_restart 是多选，值为逗号分隔的字符串如 "1,0"
            const searchValues = String(val).split(',');
            return searchValues.includes(String(item.need_restart));
          }
          const search = String(val).toLowerCase();
          const fieldValue = String((item as Record<string, any>)[key] ?? '').toLowerCase();
          return fieldValue.includes(search);
        }),
      );
    }

    return data;
  });

  // 重启生效筛选选项
  const needRestartFilter = {
    component: markRaw(MultipleSelect),
    name: t('重启生效'),
    props: {
      list: [
        { label: t('是'), value: '1' },
        { label: t('否'), value: '0' },
      ],
    },
    showConfirmAndReset: true,
  };

  // 差异对比数据
  const diffItems = computed(() =>
    editItems.value.map((item) => {
      const origin = originItems.value.find((o) => o.conf_name === item.conf_name);
      return {
        conf_name: item.conf_name,
        isChanged: origin?.conf_value !== item.conf_value,
        newValue: item.conf_value ?? '--',
        originValue: origin?.conf_value ?? '--',
      };
    }),
  );

  watch(isShow, () => {
    if (isShow.value) {
      editItems.value = _.cloneDeep(props.data);
      originItems.value = _.cloneDeep(props.data);
      filterValue.value = {};
      currentStep.value = 1;
    }
  });

  const handleFilterChange = (val: Record<string, string>) => {
    filterValue.value = val;
  };

  const handleRemoveItem = (index: number) => {
    editItems.value.splice(index, 1);
  };

  const handleNextStep = () => {
    currentStep.value = 2;
  };

  const handlePrevStep = () => {
    currentStep.value = 1;
  };

  const handleSave = async () => {
    // 后端校验合法性
    try {
      await validateConfItems(
        editItems.value.map((item) => ({
          conf_name: item.conf_name,
          op_type: 'update',
          value_allowed: item.value_allowed,
          value_default: item.conf_value ?? '',
          value_type: item.value_type ?? '',
          value_type_sub: item.value_type_sub ?? '',
        })),
      );
    } catch {
      return;
    }

    submitLoading.value = true;
    try {
      await updateBusinessConfig({
        bk_biz_id: props.fetchParams.bk_biz_id,
        conf_items: editItems.value.map((item) => Object.assign(item, { op_type: 'update' })),
        conf_type: props.fetchParams.conf_type,
        confirm: 0,
        description: '',
        level_info: props.fetchParams.level_info,
        level_name: props.fetchParams.level_name,
        level_value: props.fetchParams.level_value,
        meta_cluster_type: props.fetchParams.meta_cluster_type,
        name: props.fetchParams.name || '',
        publish_description: '',
        version: props.fetchParams.version,
      });
      messageSuccess(t('操作成功，n 个参数已转为自定义', { n: editItems.value.length }));
      emit('saved');
      handleClose();
    } finally {
      submitLoading.value = false;
    }
  };

  const handleClose = () => {
    isShow.value = false;
    emit('close');
  };
</script>

<style lang="less" scoped>
  .config-edit-diff-sideslider {
    .batch-edit-steps {
      position: sticky;
      top: 0;
      z-index: 10;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 48px;
      background: #fff;
      border-bottom: 1px solid #eaebf0;
    }

    .step-item {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .step-circle {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      font-size: 12px;
      border-radius: 32px;

      &.is-active {
        color: #fff;
        background: #3a84ff;
      }

      &.is-done {
        color: #3a84ff;
        background: #f0f5ff;
      }

      &.is-pending {
        color: #63656e;
        background: #eaebf0;
      }
    }

    .step-label {
      font-size: 14px;
      color: #313238;
    }

    .step-line {
      width: 100px;
      height: 0;
      margin: 0 16px;
      border-top: 1px solid #3a84ff;
    }

    .batch-edit-body {
      padding: 16px 24px;
      background: #f5f7fa;
    }

    .batch-edit-card {
      padding: 16px 24px;
      background: #fff;

      :deep(.db-card-content) {
        padding: 0;
      }
    }

    .batch-edit-subtitle {
      position: relative;
      padding-left: 8px;
      margin-left: 8px;
      font-size: 14px;
      line-height: 22px;
      color: #979ba5;

      &::before {
        position: absolute;
        top: 50%;
        left: 0;
        width: 1px;
        height: 16px;
        background: #dcdee5;
        content: '';
        transform: translateY(-50%);
      }
    }

    .batch-edit-count {
      font-size: 14px;
      color: #979ba5;
    }

    .no-constraint-text {
      color: #c4c6cc;
    }

    .diff-table-scroll {
      overflow: auto;
    }

    .diff-table {
      width: 100%;
      font-size: 12px;
      border-collapse: collapse;
      table-layout: fixed;

      tr {
        border-bottom: 1px solid #dcdee5;
      }

      th,
      td {
        width: 33.33%;
        padding: 10px 16px;
        text-align: left;
      }

      th {
        font-weight: normal;
        color: #313238;
        background: #f0f1f5;
      }

      td {
        color: #63656e;
      }

      td.is-changed {
        background: #fdf4e8;
      }
    }

    .diff-cell-text {
      display: inline-block;
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
</style>
