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
  <div ref="rootRef">
    <TableEditElement
      ref="editElementRef"
      :disabled="disabled"
      :placeholder="t('请选择文件')"
      :rules="rules"
      :value="modelValue"
      @clear="handleValueClear">
      {{ formatLogName(modelValue) }}
      <template #prepend>
        <DbIcon
          class="file-flag"
          type="wenjian" />
      </template>
      <template #append>
        <DbIcon
          class="focused-flag"
          type="down-big" />
      </template>
    </TableEditElement>
    <div style="display: none">
      <div ref="popRef">
        <div class="tab-header">
          <div
            v-for="item in tabOptions"
            :key="item.name"
            v-bk-tooltips="{
              content: item.hoverText || '',
              disabled: !item.hoverText,
            }"
            class="tab-header-item"
            :class="{ 'is-active': recordType === item.name }"
            @click="hanldeChangeTab(item.name)">
            {{ item.label }}
          </div>
        </div>

        <div v-if="recordType === OperateType.MANUAL">
          <div class="search-input-box">
            <BkInput
              v-model="searchKey"
              behavior="simplicity"
              :placeholder="t('请输入关键字')">
              <template #prefix>
                <span style="font-size: 14px; color: #979ba5">
                  <DbIcon type="search" />
                </span>
              </template>
            </BkInput>
          </div>
          <div
            v-if="renderList.length < 1"
            style="color: #63656e; text-align: center">
            {{ t('') }}
          </div>
          <div
            v-else
            class="options-list">
            <div
              v-for="item in renderList"
              :key="item.value"
              class="option-item"
              :class="{
                active: item.value === modelValue?.backup_id,
              }"
              @click="handleLogListSelect(item)">
              <BkPopover
                boundary="document.body"
                :offset="26"
                placement="right"
                theme="light"
                :z-index="999999">
                <div>{{ item.label }}</div>
                <template #content>
                  <div style="line-height: 20px; color: #63656e">
                    <div style="font-weight: bold">{{ t('起止时间：') }}</div>
                    <div>
                      {{ item.payload.role }}
                      <span>:</span>
                      {{ formatDateToUTC(item.payload.start_time) }}
                      <span>~</span>
                      {{ formatDateToUTC(item.payload.end_time) }}
                    </div>
                    <div style="display: flex; align-items: center">
                      <DbIcon
                        svg
                        :type="item.isMissed ? 'sync-waiting-01' : 'sync-success'" />
                      <I18nT keypath="备份记录（d）：预期返回 n 个 DB 的备份记录，实际返回 m 个">
                        <span>{{ item.isMissed ? t('缺失') : t('完整') }}</span>
                        <span style="padding: 0 4px; font-weight: bold">{{ item.payload.expected_cnt }}</span>
                        <span
                          :style="{
                            padding: '0 4px',
                            'font-weight': 'bold',
                            color: item.isMissed ? '#ff9c01' : '#2DCB56',
                          }">
                          {{ item.payload.real_cnt }}
                        </span>
                      </I18nT>
                    </div>
                  </div>
                </template>
              </BkPopover>
            </div>
          </div>
        </div>

        <div
          v-else-if="recordType === OperateType.MATCH"
          ref="dateRenderRef"
          class="date-picker-render">
          <BkDatePicker
            ref="datePickerRef"
            v-model="autoMatchDateTime"
            :clearable="false"
            :open="open"
            type="datetime"
            @pick-success="handlePickSuccess">
            <template #trigger>
              <a
                ref="dateTriggerRef"
                href="javascript:void(0)"
                @click="handleDatePickerTrigger" />
            </template>
          </BkDatePicker>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { computed, onBeforeUnmount, onMounted, ref, type UnwrapRef, watch } from 'vue';
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { queryBackupLogs, queryLatestBackupLog } from '@services/source/sqlserver';

  import { useDebouncedRef, useTimeZoneFormat } from '@hooks';

  import TableEditElement from '@components/render-table/columns/element/Index.vue';

  import { encodeRegexp } from '@utils';

  interface Props {
    clusterId?: number;
    disabled: boolean;
  }

  interface Expose {
    getValue: () => Promise<ServiceReturnType<typeof queryBackupLogs>[number]>;
  }

  const props = withDefaults(defineProps<Props>(), {
    clusterId: undefined,
    disabled: false,
  });

  let tippyIns: Instance;
  const { t } = useI18n();

  enum OperateType {
    MANUAL = 'maunal',
    MATCH = 'match',
  }
  const tabOptions = [
    {
      label: t('指定备份记录'),
      name: OperateType.MANUAL,
    },
    {
      label: t('指定时间自动匹配'),
      name: OperateType.MATCH,
      hoverText: t('自动匹配指定日期前的最新全库备份'),
    },
  ];

  const { format: formatDateToUTC } = useTimeZoneFormat();
  const searchKey = useDebouncedRef('');

  const modelValue = defineModel<ServiceReturnType<typeof queryBackupLogs>[number]>();

  const formatLogName = (logData: UnwrapRef<typeof modelValue>) =>
    logData ? `${logData.role} ${formatDateToUTC(logData.start_time)}` : '';

  const rootRef = ref();
  const popRef = ref();
  const editElementRef = ref<ComponentExposed<typeof TableEditElement>>();
  const dateTriggerRef = ref();
  const datePickerRef = ref();
  const dateRenderRef = ref();
  const isShowPop = ref(false);
  const open = ref(false);
  const recordType = ref(OperateType.MANUAL);
  const autoMatchDateTime = ref('');

  const backupLogListMemo = shallowRef<ServiceReturnType<typeof queryBackupLogs>>([]);

  const logRecordOptions = computed(() =>
    backupLogListMemo.value.map((item) => ({
      value: item.backup_id,
      label: formatLogName(item),
      payload: item,
      isMissed: item.expected_cnt < item.real_cnt,
    })),
  );

  const renderList = computed(() =>
    logRecordOptions.value.reduce<UnwrapRef<typeof logRecordOptions>>((result, item) => {
      const reg = new RegExp(encodeRegexp(searchKey.value), 'i');
      if (reg.test(item.label)) {
        result.push(item);
      }
      return result;
    }, []),
  );

  const rules = [
    {
      validator: () => (recordType.value === OperateType.MANUAL ? Boolean(modelValue.value) : true),
      message: t('备份记录不能为空'),
    },
    {
      validator: () => {
        // 非日期输入无需调接口匹配最近记录，跳过该校验
        if (recordType.value === OperateType.MANUAL) {
          return true;
        }
        return queryLatestBackupLog({
          cluster_id: props.clusterId as number,
          rollback_time: autoMatchDateTime.value,
        }).then((data) => {
          if (!data) {
            modelValue.value = undefined;
            return false;
          }
          backupLogListMemo.value.push(data);
          modelValue.value = data;
          return true;
        });
      },
      message: t('暂无与指定时间最近的备份记录'),
    },
  ];

  const fetchLogData = () => {
    backupLogListMemo.value = [];
    queryBackupLogs({
      cluster_id: props.clusterId as number,
    }).then((dataList) => {
      backupLogListMemo.value = dataList;
    });
  };

  watch(
    () => [props.clusterId],
    () => {
      if (!props.clusterId) {
        return;
      }
      fetchLogData();
    },
    {
      immediate: true,
    },
  );

  watch(
    modelValue,
    () => {
      recordType.value = OperateType.MANUAL;
      autoMatchDateTime.value = '';
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.disabled,
    () => {
      nextTick(() => {
        props.disabled ? tippyIns?.disable() : tippyIns?.enable();
      });
    },
    {
      immediate: true,
    },
  );

  const hanldeChangeTab = (tabName: OperateType) => {
    recordType.value = tabName;
    autoMatchDateTime.value = '';
    if (tabName === OperateType.MATCH) {
      nextTick(() => {
        dateTriggerRef.value.click();
      });
    }
  };

  // 手动选择
  const handleLogListSelect = (item: UnwrapRef<typeof logRecordOptions>[number]) => {
    modelValue.value = _.find(backupLogListMemo.value, (logItem) => logItem.backup_id === item.value);
    tippyIns.hide();
  };
  // 删除值
  const handleValueClear = () => {
    modelValue.value = undefined;
  };
  // 触发日期选择器
  const handleDatePickerTrigger = () => {
    open.value = true;
    nextTick(() => {
      const pickerElement = datePickerRef.value.$el;
      const pickerBody = pickerElement!.querySelector('.bk-picker-panel-body');
      if (pickerElement && pickerBody) {
        dateRenderRef.value.replaceChild(pickerBody, pickerElement);
        open.value = false;
      }
    });
  };
  // 选择日期回调
  const handlePickSuccess = () => {
    tippyIns.hide();
  };

  onMounted(() => {
    tippyIns = tippy(rootRef.value as SingleTarget, {
      content: popRef.value,
      placement: 'bottom-start',
      appendTo: () => document.body,
      theme: 'rollback-mode-select light',
      maxWidth: 'none',
      trigger: 'click',
      interactive: true,
      arrow: false,
      offset: [0, 8],
      onShow: () => {
        isShowPop.value = true;
      },
      onHide: () => {
        isShowPop.value = false;
        searchKey.value = '';
        editElementRef.value!.getValue();
      },
    });
    tippyIns.disable();
  });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
    }
  });

  defineExpose<Expose>({
    getValue() {
      return editElementRef.value!.getValue().then(() => (modelValue.value ? modelValue.value : Promise.reject()));
    },
  });
</script>
<style lang="less">
  .rollback-mode-select {
    &.is-seleced {
      &:hover {
        .remove-btn {
          display: block;
        }

        .focused-flag {
          display: none;
        }
      }
    }

    &.is-focused {
      border: 1px solid #3a84ff;

      .focused-flag {
        transform: rotateZ(-90deg);
      }
    }

    .focused-flag {
      position: absolute;
      right: 4px;
      font-size: 14px;
      transition: all 0.15s;
    }

    .remove-btn {
      position: absolute;
      right: 4px;
      z-index: 1;
      display: none;
      font-size: 16px;
      color: #c4c6cc;
      transition: all 0.15s;

      &:hover {
        color: #979ba5;
      }
    }
  }

  .tippy-box[data-theme~='rollback-mode-select'] {
    .tippy-content {
      width: 260px;
      padding: 0;
      font-size: 12px;
      line-height: 32px;
      color: #26323d;
      background-color: #fff;
      border-radius: 2px;
      user-select: none;

      .search-input-box {
        padding: 0 12px;

        .bk-input--text {
          background-color: #fff;
        }
      }

      .options-list {
        max-height: 300px;
        margin: 4px 0;
        overflow-y: auto;
      }

      .option-item {
        height: 32px;
        padding: 0 12px;
        overflow: hidden;
        line-height: 32px;
        text-overflow: ellipsis;
        white-space: pre;

        &:hover {
          color: #3a84ff;
          cursor: pointer;
          background-color: #f5f7fa;
        }

        &.active {
          color: #3a84ff;
        }

        &.disabled {
          color: #c4c6cc;
          cursor: not-allowed;
          background-color: transparent;
        }
      }

      .option-item-value {
        padding-left: 8px;
        overflow: hidden;
        color: #979ba5;
        text-overflow: ellipsis;
        word-break: keep-all;
        white-space: nowrap;
      }

      .tab-header {
        display: flex;

        .tab-header-item {
          display: flex;
          height: 36px;
          font-size: 12px;
          line-height: 20px;
          letter-spacing: 0;
          color: #63656e;
          cursor: pointer;
          background: #fafbfd;
          border-right: 1px solid #dcdee5;
          border-bottom: 1px solid #dcdee5;
          flex: 1;
          justify-content: center;
          align-items: center;

          &:hover {
            color: #3a84ff;
          }
        }

        .is-active {
          color: #3a84ff;
          background: #fff;
          border-bottom-color: #fff;
          border-radius: 2px 0 0;
        }
      }

      .date-picker-render {
        position: relative;
        height: 330px;

        .bk-picker-panel-body {
          width: 100% !important;
        }
      }
    }
  }
</style>
