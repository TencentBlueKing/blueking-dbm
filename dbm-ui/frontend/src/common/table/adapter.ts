import _ from 'lodash';

import { makeMap } from './utils';

export const columnConfig = (bkColumnConfig: any) => {
  const vxeColumnConfig = {
    ...bkColumnConfig,
    slots: {},
  };

  if (bkColumnConfig.label) {
    if (_.isString(bkColumnConfig.label)) {
      vxeColumnConfig.title = bkColumnConfig.label;
    } else if (_.isFunction(bkColumnConfig.label)) {
      const renderLabel = bkColumnConfig.label;
      Object.assign(vxeColumnConfig.slots, {
        header: (payload: any) => {
          const res = renderLabel({
            column: payload.column,
            index: payload.$rowIndex,
          });

          return res;
        },
      });
    }
    delete vxeColumnConfig.label;
  }

  if (_.has(bkColumnConfig, 'sort')) {
    vxeColumnConfig.sortable = bkColumnConfig.sort;
    delete vxeColumnConfig.sort;
  }

  if (bkColumnConfig.filter && bkColumnConfig.filter.list) {
    const checkedMap = makeMap(bkColumnConfig.filter.checked || []);
    vxeColumnConfig.filters = bkColumnConfig.filter.list.map((item: any) => ({
      label: item.text,
      value: item.value,
      checked: Boolean(checkedMap[item.value]),
    }));
    vxeColumnConfig.filterMultiple = true;
    delete vxeColumnConfig.filter;
  }

  if (bkColumnConfig.render) {
    const cellRender = bkColumnConfig.render;
    Object.assign(vxeColumnConfig.slots, {
      default: (payload: any) => cellRender(payload),
    });
    delete vxeColumnConfig.render;
  }

  if (bkColumnConfig.renderHead) {
    const headRender = bkColumnConfig.renderHead;
    Object.assign(vxeColumnConfig.slots, {
      header: (payload: any) =>
        headRender({
          column: payload.column,
        }),
    });
    delete vxeColumnConfig.renderHead;
  }

  delete vxeColumnConfig.label;
  delete vxeColumnConfig.sort;
  delete vxeColumnConfig.textAlign;

  // 废弃属性
  delete vxeColumnConfig.children;
  delete vxeColumnConfig.titleHelp;

  return vxeColumnConfig;
};

export const tableConfig = (bkTableConfig: any) => {
  const bkTableConfigMemo = _.cloneDeep(bkTableConfig);
  const vxeTableConfig = {
    ...bkTableConfig,
  };

  if (bkTableConfigMemo.columns) {
    delete vxeTableConfig.columns;
  }
  if (bkTableConfigMemo.rowClass) {
    if (typeof bkTableConfigMemo.rowClass === 'string') {
      vxeTableConfig.rowClassName = bkTableConfigMemo.rowClas;
    } else if (typeof bkTableConfigMemo.rowClass === 'function') {
      const { rowClass } = bkTableConfigMemo;

      vxeTableConfig.rowClassName = ({ row }: { row: any }) => rowClass(row);
    }
  }

  delete vxeTableConfig.style;
  delete vxeTableConfig['row-class'];
  delete vxeTableConfig.class;
  delete vxeTableConfig['show-overflow-tooltip'];
  delete vxeTableConfig.pagination;
  delete vxeTableConfig['pagination-height'];
  delete vxeTableConfig['remote-pagination'];
  delete vxeTableConfig['selection-key'];
  delete vxeTableConfig.settings;
  delete vxeTableConfig.spellcheck;
  delete vxeTableConfig.isrowselectenable;

  return vxeTableConfig;
};
