import { Popover } from 'bkui-vue';
import _ from 'lodash';
import { Checkbox, Radio } from 'tdesign-vue-next';
import { defineComponent, getCurrentInstance, type Ref, ref, shallowRef } from 'vue';
import { useI18n } from 'vue-i18n';

import { TableColumn } from '@blueking/tdesign-ui';

import DbIcon from '@components/db-icon/index';

import { type Exposes, type Props } from '../IndexNew.vue';

export const useSelect = (
  props: Props,
  tableData: Ref<{ results: Record<string, any>[] }>,
  options?: { callback: () => void },
) => {
  const { t } = useI18n();
  const currentInstance = getCurrentInstance();

  const selectedRowMap = shallowRef<Record<string | number, Record<any, any>>>({});
  const isWholeChecked = ref(false);

  // 是否本页全选
  const isCurrentPageAllSelected = computed(() => {
    if (isWholeChecked.value) {
      return false;
    }
    if (tableData.value.results.length < 1) {
      return false;
    }
    const selectedMap = { ...selectedRowMap.value };
    // eslint-disable-next-line @typescript-eslint/prefer-for-of
    for (let i = 0; i < tableData.value.results.length; i++) {
      if (!selectedMap[_.get(tableData.value.results[i], props.rowKey)]) {
        return false;
      }
    }
    return true;
  });

  const handleTogglePageSelect = (checked: boolean) => {
    const selectedMap = { ...selectedRowMap.value };
    tableData.value.results.forEach((dataItem: any) => {
      if (checked) {
        if (!props.disableSelectMethod?.(dataItem)) {
          selectedMap[_.get(dataItem, props.rowKey)] = dataItem;
        }
      } else {
        delete selectedMap[_.get(dataItem, props.rowKey)];
      }
    });
    isWholeChecked.value = false;
    selectedRowMap.value = selectedMap;
    options?.callback();
  };

  const handleWholeSelect = () => {
    (currentInstance!.exposeProxy as Exposes).fetchAllData().then((results) => {
      const selectedMap = { ...selectedRowMap.value };
      results.forEach((dataItem: any) => {
        if (props.disableSelectMethod?.(dataItem)) {
          return;
        }
        selectedMap[_.get(dataItem, props.rowKey)] = dataItem;
      });
      selectedRowMap.value = selectedMap;
      isWholeChecked.value = true;
      options?.callback();
    });
  };

  const handleSelect = (rowData: Record<string, any>) => {
    if (props.selectSingle) {
      selectedRowMap.value = {};
    }
    const selectedMap = { ...selectedRowMap.value };
    if (selectedMap[_.get(rowData, props.rowKey)]) {
      delete selectedMap[_.get(rowData, props.rowKey)];
    } else {
      selectedMap[_.get(rowData, props.rowKey)] = rowData;
    }
    isWholeChecked.value = false;
    selectedRowMap.value = selectedMap;
    options?.callback();
  };

  const handleClearWholeSelect = () => {
    selectedRowMap.value = {};
    isWholeChecked.value = false;
    options?.callback();
  };

  const selectColumn = defineComponent({
    setup() {
      return () => (
        <TableColumn
          colKey='row-select'
          fixed='left'
          resizable={false}
          width={60}>
          {{
            default: ({ row }: { row: any }) => {
              const selectDisabled = props.disableSelectMethod ? props.disableSelectMethod(row) : false;
              return (
                <span
                  v-bk-tooltips={{
                    content: _.isString(selectDisabled) ? selectDisabled : t('禁止选择'),
                    disabled: !selectDisabled,
                  }}>
                  {props.selectSingle ? (
                    <Radio
                      disabled={Boolean(selectDisabled)}
                      label={() => true}
                      modelValue={Boolean(selectedRowMap.value[row[props.rowKey]])}
                      onChange={() => handleSelect(row)}
                    />
                  ) : (
                    <Checkbox
                      disabled={Boolean(selectDisabled)}
                      modelValue={Boolean(selectedRowMap.value[row[props.rowKey]])}
                      style='width: 16px; height: 16px;'
                      onChange={() => handleSelect(row)}
                    />
                  )}
                </span>
              );
            },
            title: () =>
              !props.selectSingle && (
                <div class='db-table-select-cell'>
                  {isWholeChecked.value ? (
                    <div
                      class='db-table-whole-check'
                      onClick={handleClearWholeSelect}
                    />
                  ) : (
                    <>
                      {isCurrentPageAllSelected.value ? (
                        <Checkbox
                          key='page'
                          modelValue={true}
                          style='width: 16px;'
                          onChange={handleTogglePageSelect}
                        />
                      ) : (
                        <Checkbox
                          key='all'
                          style='width: 16px;'
                          onChange={handleWholeSelect}
                        />
                      )}
                    </>
                  )}
                  <Popover
                    v-slots={{
                      content: () => (
                        <div class='db-table-select-plan'>
                          <div
                            class={`plan-item ${isCurrentPageAllSelected.value ? 'is-selected' : ''}`}
                            onClick={() => handleTogglePageSelect(true)}>
                            {t('本页全选')}
                          </div>
                          <div
                            class={`plan-item ${isWholeChecked.value ? 'is-selected' : ''}`}
                            onClick={handleWholeSelect}>
                            {t('跨页全选')}
                          </div>
                        </div>
                      ),
                      default: () => (
                        <DbIcon
                          class='select-menu-flag'
                          type='down-big'
                        />
                      ),
                    }}
                    arrow={false}
                    placement='bottom-start'
                    theme='light db-table-select-menu'
                    trigger='hover'
                  />
                </div>
              ),
          }}
        </TableColumn>
      );
    },
  });

  return {
    handleClearWholeSelect,
    isWholeChecked,
    selectColumn,
    selectedRowMap,
  };
};
