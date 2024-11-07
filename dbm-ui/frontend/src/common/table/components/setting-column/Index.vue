<template>
  <div
    v-if="isShow"
    class="bk-vxe-table-setting-column-btn">
    <div ref="handler">
      <CogShape @click="handleShowPopover" />
    </div>
    <div
      ref="content"
      class="bk-vxe-table-setting-menu">
      <template v-if="isShowPopover">
        <ActionTab v-model="actionPanel" />
        <FieldList
          v-if="actionPanel === 'field'"
          v-model="settingsModel.checked"
          :list="settingsModel.fields" />
        <Others
          v-if="actionPanel === 'others'"
          v-model="settingsModel.size">
          <slot />
        </Others>
      </template>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { CogShape } from 'bkui-vue/lib/icon';
  import _ from 'lodash';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { ref, shallowReactive, useTemplateRef } from 'vue';

  import { type VxeTableDefines } from '@blueking/vxe-table';

  import { makeMap } from '../../utils';

  import ActionTab from './components/ActionTab.vue';
  import FieldList from './components/FieldList.vue';
  import Others from './components/Others.vue';
  import useOutSideClick from './useOutSideClick';

  export interface ISettings {
    fields: {
      /**
       * 即将废弃，不建议使用，被 title 替换
       * @deprecated
       */
      label: string;
      title: string;
      field: string;
      disabled: boolean;
    }[];
    checked: string[];
    size: 'medium' | 'small' | 'mini';
  }

  interface Props {
    getTable: () => any;
    isShow: boolean;
    settings?: ISettings;
  }

  interface Emits {
    (e: 'change', value: ISettings): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  let tippyIns: Instance;

  const handleRef = useTemplateRef('handler');
  const contentRef = useTemplateRef('content');
  const isShowPopover = ref(false);
  const actionPanel = ref('field');

  const settingsModel = shallowReactive<ISettings>({
    fields: [],
    checked: [],
    size: 'small',
  });

  watch(
    () => props.settings,
    () => {
      if (!props.getTable() || !props.settings) {
        return;
      }
      if (props.settings.checked && props.settings.checked.length > 0) {
        const allShowColumnFieldMap = makeMap(props.settings.checked);
        props
          .getTable()
          .getTableColumn()
          .fullColumn.forEach((columnInfo: VxeTableDefines.ColumnInfo) => {
            if (!columnInfo.field) {
              return;
            }
            if (allShowColumnFieldMap[columnInfo.field]) {
              props.getTable().showColumn(columnInfo);
            } else {
              props.getTable().hideColumn(columnInfo);
            }
          });
      }
    },
    {
      immediate: true,
    },
  );

  useOutSideClick(() => {
    if (!isShowPopover.value) {
      return;
    }
    isShowPopover.value = false;
    const tableRef = props.getTable();

    const showColumnFieldMap = makeMap(settingsModel.checked);

    const hideColumnFieldMap = settingsModel.fields.reduce<Record<string, boolean>>((result, item) => {
      if (!showColumnFieldMap[item.field]) {
        Object.assign(result, {
          [item.field]: true,
        });
      }
      return result;
    }, {});

    props
      .getTable()
      .getTableColumn()
      .fullColumn.forEach((columnInfo: VxeTableDefines.ColumnInfo) => {
        if (!columnInfo.field || !hideColumnFieldMap[columnInfo.field]) {
          tableRef.showColumn(columnInfo);
        } else {
          tableRef.hideColumn(columnInfo);
        }
      });
    emits('change', { ...settingsModel });
  });

  const handleShowPopover = () => {
    isShowPopover.value = true;
  };

  onMounted(() => {
    if (!props.isShow) {
      return;
    }
    tippyIns = tippy(handleRef.value as SingleTarget, {
      content: contentRef.value as Element,
      placement: 'bottom-end',
      appendTo: () => document.body,
      theme: 'light bk-vxe-table-setting-column-theme',
      maxWidth: 'none',
      trigger: 'click',
      interactive: true,
      arrow: false,
      offset: [0, 12],
      zIndex: 999999,
      hideOnClick: true,
      onShown() {
        isShowPopover.value = true;

        if (props.settings && props.settings.fields.length > 0) {
          settingsModel.fields = [...props.settings.fields];
        } else {
          settingsModel.fields = _.filter(props.getTable().getTableColumn().fullColumn, (item) => item.field);
        }
        if (props.settings && props.settings.size) {
          settingsModel.size = props.settings.size;
        }

        setTimeout(() => {
          if (props.settings && props.settings.checked) {
            settingsModel.checked = [...(props.settings.checked || [])];
          }
        });
      },
      onHidden() {
        isShowPopover.value = false;
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
</script>
<style lang="less">
  .bk-vxe-table {
    .vxe-table {
      &.size--mini {
        .bk-vxe-table-setting-column-btn {
          min-height: 36px;
        }
      }

      &.size--small {
        .bk-vxe-table-setting-column-btn {
          min-height: 40px;
        }
      }

      &.size--medium {
        .bk-vxe-table-setting-column-btn {
          min-height: 44px;
        }
      }
    }
  }

  .bk-vxe-table-setting-column-btn {
    display: flex;
    width: 100%;
    height: 100%;
    font-size: 12px;
    color: #c4c6cc;
    cursor: pointer;
    align-items: center;
    justify-content: center;

    & > div {
      display: flex;
      width: 100%;
      height: 100%;
      align-items: center;
      justify-content: center;
    }
  }

  .tippy-box[data-theme~='bk-vxe-table-setting-column-theme'] {
    min-width: 240px;

    .tippy-content {
      padding: 0;
    }

    .action-tab-wrapper {
      display: flex;
      height: 42px;
      max-height: 500px;
      overflow-y: scroll;
      font-size: 14px;
      color: #63656e;
      background: #f0f1f5;

      .tab-item {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.1s;

        &.active {
          color: #3a84ff;
          background: #fff;
        }
      }
    }

    .field-list-wrapper {
      max-height: 300px;
      padding: 0 16px;
      margin: 8px 0;
      overflow-y: auto;

      .bk-checkbox-group {
        display: block;
      }

      .field-list-item {
        display: flex;
        height: 32px;
        align-items: center;
      }
    }
  }
</style>
