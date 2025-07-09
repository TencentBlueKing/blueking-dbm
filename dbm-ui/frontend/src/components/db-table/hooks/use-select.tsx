import { Checkbox, Popover } from 'bkui-vue';
import { defineComponent, ref, shallowRef } from 'vue';
import { useI18n } from 'vue-i18n';

import { TableColumn } from '@blueking/table';

import DbIcon from '@components/db-icon/index';

import { type Props } from '../IndexNew.vue';
import _ from 'lodash';

export const useSelect = (props: Props, tableData: Record<string, any>[]) => {
  const { t } = useI18n();

  const showSelectAllPage = ref(false);
  const rowSelectMap = shallowRef<Record<string | number, Record<any, any>>>({});
  const isWholeChecked = ref(false);

  // 是否本页全选
  const isCurrentPageAllSelected = computed(() => {
    if (isWholeChecked.value) {
      return false;
    }
    if (tableData.length < 1) {
      return false;
    }
    const selectMap = { ...rowSelectMap.value };
    // eslint-disable-next-line @typescript-eslint/prefer-for-of
    for (let i = 0; i < tableData.length; i++) {
      if (!selectMap[_.get(tableData[i], props.primaryKey)]) {
        return false;
      }
    }
    return true;
  });

  const handleClearWholeSelect = () => {
    rowSelectMap.value = {};
    isWholeChecked.value = false;
  };

  const handleTogglePageSelect = (checked: boolean) => {
    const selectMap = { ...rowSelectMap.value };
    tableData.forEach((dataItem: any) => {
      if (checked) {
        if (!props.disableSelectMethod?.(dataItem)) {
          selectMap[_.get(dataItem, props.primaryKey || 'id')] = dataItem;
        }
      } else {
        delete selectMap[_.get(dataItem, props.primaryKey || 'id')];
      }
    });
    if (!checked) {
      isWholeChecked.value = false;
    }
    rowSelectMap.value = selectMap;
  };

  const handleWholeSelect = () => {
    console.log('handleWholeSelect');
  };

  const handlePageSelect = () => {
    const selectMap = { ...rowSelectMap.value };
    tableData.forEach((dataItem: any) => {
      if (props.disableSelectMethod?.(dataItem)) {
        return;
      }
      selectMap[_.get(dataItem, props.primaryKey || 'id')] = dataItem;
    });
    rowSelectMap.value = selectMap;
    isWholeChecked.value = false;
  };

  const selectColumn = defineComponent({
    setup() {
      return () => (
        <TableColumn>
          {{
            default: () => (
              <div>
                <Checkbox />
              </div>
            ),
            title: () => (
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
                        label={true}
                        modelValue={true}
                        onChange={handleTogglePageSelect}
                      />
                    ) : (
                      <Checkbox
                        key='all'
                        onChange={handleWholeSelect}
                      />
                    )}
                    {showSelectAllPage.value && (
                      <Popover
                        v-slots={{
                          content: () => (
                            <div class='db-table-select-plan'>
                              <div
                                class={`plan-item ${isCurrentPageAllSelected.value ? 'is-selected' : ''}`}
                                onClick={handlePageSelect}>
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
                    )}
                  </>
                )}
              </div>
            ),
          }}
        </TableColumn>
      );
    },
  });

  return {
    isWholeChecked,
    rowSelectMap,
    selectColumn,
  };
};
