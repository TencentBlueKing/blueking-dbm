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
      :value="selectBackupId"
      @clear="handleValueClear">
      {{ renderText }}
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
                active: item.value === selectBackupId,
              }"
              @click="handleSelect(item)">
              <span>{{ item.label }}</span>
            </div>
          </div>
        </div>

        <div
          v-else-if="recordType === OperateType.MATCH"
          ref="dateRenderRef"
          class="date-picker-render">
          <BkDatePicker
            ref="datePickerRef"
            :clearable="false"
            :open="open"
            type="datetime"
            :value="selectBackupId"
            @change="handleDatePickerChange"
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
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { computed, onBeforeUnmount, onMounted, ref, type UnwrapRef, watch } from 'vue';
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { queryBackupLogs, queryLatestBackupLog } from '@services/source/sqlserver';

  import { useDebouncedRef } from '@hooks';

  import { useTimeZone } from '@stores';

  import TableEditElement from '@components/render-table/columns/element/Index.vue';

  import { encodeRegexp } from '@utils';

  interface Props {
    clusterId?: number;
    backupid?: string;
    disabled: boolean;
  }

  interface Expose {
    getValue: () => Promise<ServiceReturnType<typeof queryBackupLogs>[number]>;
  }

  const props = withDefaults(defineProps<Props>(), {
    clusterId: undefined,
    backupid: '',
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

  const timeZoneStore = useTimeZone();
  const searchKey = useDebouncedRef('');

  const rootRef = ref();
  const popRef = ref();
  const editElementRef = ref<ComponentExposed<typeof TableEditElement>>();
  const dateTriggerRef = ref();
  const datePickerRef = ref();
  const dateRenderRef = ref();
  const selectBackupId = ref<string>('');
  const isShowPop = ref(false);
  const isError = ref(false);
  const open = ref(false);
  const recordType = ref(OperateType.MANUAL);

  const logRecordOptions = shallowRef<Array<{ value: string; label: string }>>([]);
  const backupLogListMemo = shallowRef<ServiceReturnType<typeof queryBackupLogs>>([]);

  const renderList = computed(() =>
    logRecordOptions.value.reduce<UnwrapRef<typeof logRecordOptions>>((result, item) => {
      const reg = new RegExp(encodeRegexp(searchKey.value), 'i');
      if (reg.test(item.label)) {
        result.push(item);
      }
      return result;
    }, []),
  );

  const renderText = computed(() => {
    const item = _.find(logRecordOptions.value, (item) => item.value === selectBackupId.value);
    return !item ? '' : item.label;
  });

  const rules = [
    {
      validator: () => Boolean(selectBackupId.value),
      message: t('备份记录不能为空'),
    },
    {
      validator: () => {
        // 非日期输入无需调接口匹配最近记录，跳过该校验
        if (!isDateType(selectBackupId.value)) {
          return true;
        }
        return queryLatestBackupLog({
          cluster_id: props.clusterId as number,
          rollback_time: selectBackupId.value,
        }).then((data) => {
          if (!data) {
            selectBackupId.value = '';
            return false;
          }
          backupLogListMemo.value.push(data);
          selectBackupId.value = data.backup_id;
          return true;
        });
      },
      message: t('暂无与指定时间最近的备份记录'),
    },
  ];

  const fetchLogData = () => {
    logRecordOptions.value = [];
    backupLogListMemo.value = [];
    queryBackupLogs({
      cluster_id: props.clusterId as number,
    }).then((dataList) => {
      logRecordOptions.value = dataList.map((item) => ({
        value: item.backup_id,
        label: `${item.role} ${dayjs(item.start_time).tz(timeZoneStore.label).format('YYYY-MM-DD HH:mm:ss ZZ')}`,
      }));
      backupLogListMemo.value = dataList;
    });
  };

  const hanldeChangeTab = (tabName: OperateType) => {
    recordType.value = tabName;
    if (tabName === OperateType.MATCH) {
      selectBackupId.value = '';
      nextTick(() => {
        dateTriggerRef.value.click();
      });
    } else {
      fetchLogData();
    }
  };
  // 手动选择
  const handleSelect = (item: UnwrapRef<typeof logRecordOptions>[number]) => {
    selectBackupId.value = item.value;
    tippyIns.hide();
  };
  // 删除值
  const handleValueClear = () => {
    selectBackupId.value = '';
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
  const handleDatePickerChange = (date: string) => {
    selectBackupId.value = date;
  };
  // 选择日期回调
  const handlePickSuccess = () => {
    tippyIns.hide();
  };
  const isDateType = (value: string) => {
    const YYYYMMDDHHmmssReg = /[\d]{4}[\\/-]{1}[\d]{1,2}[\\/-]{1}[\d]{1,2}\s[\d]{1,2}[:][\d]{1,2}[:][\d]{1,2}/g;
    const isDate = new RegExp(YYYYMMDDHHmmssReg);
    // 非日期输入无需调接口匹配最近记录，跳过该校验
    return isDate.test(value);
  };

  watch(
    () => [props.clusterId, timeZoneStore.label],
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
    () => props.backupid,
    (newVal) => {
      if (newVal) {
        const currentRecordType = isDateType(newVal) ? OperateType.MATCH : OperateType.MANUAL;
        hanldeChangeTab(currentRecordType);
        selectBackupId.value = newVal;
      }
    },
    {
      immediate: true,
    },
  );

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
        isError.value = false;
      },
      onHide: () => {
        isShowPop.value = false;
        searchKey.value = '';
        editElementRef.value!.getValue();
      },
    });
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
      return editElementRef.value!.getValue().then(() => {
        const backupLog = _.find(backupLogListMemo.value, (item) => item.backup_id === selectBackupId.value);
        return backupLog ? backupLog : Promise.reject();
      });
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
