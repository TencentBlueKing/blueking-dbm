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
  <div
    ref="rootRef"
    class="rollback-mode-select"
    :class="{
      'is-focused': isShowPop,
      'is-error': Boolean(errorMessage),
      'is-disabled': disabled,
      'is-seleced': !!localValue,
    }">
    <div
      v-bk-tooltips="{
        content: renderText || '',
        disabled: !renderText,
      }"
      class="select-result-text">
      <span>{{ renderText }}</span>
    </div>
    <DbIcon
      v-if="clearable && localValue"
      class="remove-btn"
      type="delete-fill"
      @click.self="handleRemove" />
    <DbIcon
      class="focused-flag"
      type="down-big" />
    <div
      v-if="errorMessage"
      class="select-error">
      <DbIcon
        v-bk-tooltips="errorMessage"
        type="exclamation-fill" />
    </div>
    <div
      v-if="localValue === ''"
      class="select-placeholder">
      {{ t('请选择文件') }}
    </div>
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
            数据为空
          </div>
          <div
            v-else
            class="options-list">
            <div
              v-for="item in renderList"
              :key="item.id"
              class="option-item"
              :class="{
                active: item.id === localValue,
              }"
              @click="handleSelect(item)">
              <span>{{ item.name }}</span>
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
            :value="localValue"
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
  import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import {
    type BackupLogRecord,
    queryBackupLogFromBklog,
    queryBackupLogFromLoacal,
    queryLatesBackupLog,
  } from '@services/source/fixpointRollback';

  import { useDebouncedRef, useTimeZoneFormat } from '@hooks';

  import useValidtor, { type Rules } from '@components/render-table/hooks/useValidtor';

  import { encodeRegexp } from '@utils';

  interface IListItem {
    id: string;
    name: string;
  }

  interface Props {
    clusterId: number;
    backupid?: string;
    backupSource?: string;
    disabled?: boolean;
    clearable?: boolean;
  }

  interface Exposes {
    getValue: () => Promise<BackupLogRecord>;
  }

  const props = withDefaults(defineProps<Props>(), {
    backupid: '',
    backupSource: '',
    modelValue: '',
    disabled: false,
    clearable: false,
  });

  const { t } = useI18n();

  enum OperateType {
    MANUAL = 'maunal',
    MATCH = 'match',
  }

  const { timeZone } = useTimeZoneFormat();
  const searchKey = useDebouncedRef('');

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
  let tippyIns: Instance;
  const rootRef = ref();
  const popRef = ref();
  const dateTriggerRef = ref();
  const datePickerRef = ref();
  const dateRenderRef = ref();
  const localValue = ref<string>('');
  const isShowPop = ref(false);
  const isError = ref(false);
  const open = ref(false);
  const recordType = ref(OperateType.MANUAL);
  const logRecordOptions = shallowRef<Array<{ id: string; name: string }>>([]);
  const logRecordList = shallowRef<BackupLogRecord[]>([]);

  const isDateType = (value: string) => {
    const YYYYMMDDHHmmssReg = /[\d]{4}[\\/-]{1}[\d]{1,2}[\\/-]{1}[\d]{1,2}\s[\d]{1,2}[:][\d]{1,2}[:][\d]{1,2}/g;
    const isDate = new RegExp(YYYYMMDDHHmmssReg);
    // 非日期输入无需调接口匹配最近记录，跳过该校验
    return isDate.test(value);
  };

  const rules: Rules = [
    {
      validator: (value: string) => !!value,
      message: t('备份记录不能为空'),
    },
    {
      validator: (value: string) => {
        // 非日期输入无需调接口匹配最近记录，跳过该校验
        if (!isDateType(value)) {
          return true;
        }
        return queryLatesBackupLog({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_id: props.clusterId,
          rollback_time: value,
        }).then((data) => {
          if (!data) {
            localValue.value = '';
            return false;
          }
          logRecordList.value.push(data);
          localValue.value = data.backup_id;
          return true;
        });
      },
      message: t('暂无与指定时间最近的备份记录'),
    },
  ];

  const { message: errorMessage, validator } = useValidtor(rules);

  const renderList = computed(() =>
    logRecordOptions.value.reduce((result, item) => {
      const reg = new RegExp(encodeRegexp(searchKey.value), 'i');
      if (reg.test(item.name)) {
        result.push(item);
      }
      return result;
    }, [] as Array<IListItem>),
  );

  const renderText = computed(() => {
    const item = _.find(logRecordList.value, (i) => i.backup_id === localValue.value) as BackupLogRecord;
    return !item
      ? ''
      : `${item.mysql_role ? `${item.mysql_role} ` : ' '}${dayjs(item.backup_time).tz(timeZone.value.label).format('YYYY-MM-DD HH:mm:ss ZZ')}`;
  });

  const fetchLogData = () => {
    logRecordOptions.value = [];
    logRecordList.value = [];
    const queryBackupLog = props.backupSource === 'local' ? queryBackupLogFromLoacal : queryBackupLogFromBklog;
    queryBackupLog({
      cluster_id: props.clusterId,
    }).then((dataList) => {
      logRecordOptions.value = dataList.map((item) => ({
        id: item.backup_id,
        name: `${item.mysql_role ? `${item.mysql_role} ` : ' '} ${dayjs(item.backup_time).tz(timeZone.value.label).format('YYYY-MM-DD HH:mm:ss ZZ')}`,
      }));
      logRecordList.value = dataList;
    });
  };

  const hanldeChangeTab = (tabName: OperateType) => {
    recordType.value = tabName;
    if (tabName === OperateType.MATCH) {
      localValue.value = '';
      nextTick(() => {
        dateTriggerRef.value.click();
      });
    } else {
      fetchLogData();
    }
  };

  // 手动选择
  const handleSelect = (item: IListItem) => {
    localValue.value = item.id;
    tippyIns.hide();
  };

  // 删除值
  const handleRemove = () => {
    localValue.value = '';
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
    localValue.value = date;
  };

  // 选择日期回调
  const handlePickSuccess = () => {
    tippyIns.hide();
  };

  watch(
    () => [props.backupSource, props.clusterId, timeZone.value.label],
    () => {
      if (!props.clusterId || !props.backupSource) {
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
    (backupid) => {
      if (backupid) {
        validator(backupid);
        const currentRecordType = isDateType(backupid) ? OperateType.MATCH : OperateType.MANUAL;
        hanldeChangeTab(currentRecordType);
        localValue.value = backupid;
      }
    },
    {
      immediate: true,
    },
  );

  onMounted(() => {
    tippyIns = tippy(rootRef.value as SingleTarget, {
      content: popRef.value,
      placement: 'bottom',
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
        validator(localValue.value);
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

  defineExpose<Exposes>({
    getValue() {
      return validator(localValue.value).then(
        () => _.find(logRecordList.value, (item) => item.backup_id === localValue.value) as BackupLogRecord,
      );
    },
  });
</script>
<style lang="less">
  .rollback-mode-select {
    position: relative;
    display: flex;
    height: 42px;
    overflow: hidden;
    color: #63656e;
    cursor: pointer;
    border: 1px solid transparent;
    transition: all 0.15s;
    align-items: center;

    &:hover {
      background-color: #fafbfd;
      border-color: #a3c5fd;
    }

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

    &.is-error {
      background: #fff0f1;

      .focused-flag {
        display: none;
      }
    }

    &.is-disabled {
      pointer-events: none;
      cursor: not-allowed;
      background-color: #fafbfd;
    }

    .select-result-text {
      width: 100%;
      height: 100%;
      margin-right: 16px;
      margin-left: 16px;
      overflow: hidden;
      line-height: 42px;
      text-overflow: ellipsis;
      white-space: pre;
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

    .select-error {
      position: absolute;
      top: 0;
      right: 0;
      bottom: 0;
      display: flex;
      padding-right: 4px;
      font-size: 14px;
      color: #ea3636;
      align-items: center;
    }

    .select-placeholder {
      position: absolute;
      top: 10px;
      right: 20px;
      left: 18px;
      z-index: 1;
      height: 20px;
      overflow: hidden;
      font-size: 12px;
      line-height: 20px;
      color: #c4c6cc;
      text-overflow: ellipsis;
      white-space: nowrap;
      pointer-events: none;
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
