<template>
  <div class="bk-vxe-table-setting-column-btn">
    <div ref="handler">
      <CogShape @click="handleShowPopover" />
    </div>
    <div
      ref="content"
      class="bk-vxe-table-setting-menu">
      <ActionTab
        v-if="false"
        v-model="action" />
      <div class="field-list-wrapper">
        <BkCheckbox @change="handleChangeAll"> 全选 </BkCheckbox>
        <BkCheckboxGroup v-model="showColumnFieldList">
          <div
            v-for="item in columnList"
            :key="item.field"
            class="field-list-item">
            <BkCheckbox :label="item.field">
              {{ item.title }}
            </BkCheckbox>
          </div>
        </BkCheckboxGroup>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { CogShape } from 'bkui-vue/lib/icon';
  import _ from 'lodash';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { ref, shallowRef, useTemplateRef } from 'vue';

  import { type VxeTableDefines } from '@blueking/vxe-table';

  import { makeMap } from '../../utils';

  import ActionTab from './ActionTab.vue';
  import useOutSideClick from './useOutSideClick';

  interface Props {
    getTable: () => any;
  }

  const props = defineProps<Props>();

  let tippyIns: Instance;

  const handleRef = useTemplateRef('handler');
  const contentRef = useTemplateRef('content');
  const isShowPopover = ref(false);
  const action = ref('field');
  const showColumnFieldList = shallowRef<string[]>([]);
  const columnList = shallowRef<VxeTableDefines.ColumnInfo[]>([]);

  useOutSideClick(() => {
    if (!isShowPopover.value) {
      return;
    }
    isShowPopover.value = false;
    const tableRef = props.getTable();

    const showColumnFieldMap = makeMap(showColumnFieldList.value);

    props
      .getTable()
      .getTableColumn()
      .fullColumn.forEach((columnInfo: VxeTableDefines.ColumnInfo) => {
        if (!columnInfo.field || showColumnFieldMap[columnInfo.field]) {
          tableRef.showColumn(columnInfo);
        } else {
          tableRef.hideColumn(columnInfo);
        }
      });
  });

  const handleShowPopover = () => {
    isShowPopover.value = true;
    const { fullColumn, visibleColumn } = props.getTable().getTableColumn();
    columnList.value = _.filter(fullColumn, (item) => item.field);

    nextTick(() => {
      showColumnFieldList.value = _.filter(visibleColumn, (item) => item.field).map((item) => item.field);
    });
  };

  const handleChangeAll = (checkAll: boolean) => {
    if (checkAll) {
      showColumnFieldList.value = _.filter(props.getTable().getTableColumn().fullColumn, (item) => item.field).map(
        (item) => item.field,
      );
    } else {
      showColumnFieldList.value = showColumnFieldList.value.slice(0, 1);
    }
  };

  onMounted(() => {
    tippyIns = tippy(handleRef.value as SingleTarget, {
      content: contentRef.value,
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
      padding: 8px 16px;

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
