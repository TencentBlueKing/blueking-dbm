declare module 'vue' {
  interface GlobalComponents {
    AuthButton: typeof import('@components/auth-component/button.vue').default;
    AuthOption: typeof import('@components/auth-component/option.vue').default;
    AuthRouterLink: typeof import('@components/auth-component/router-link.vue').default;
    AuthSwitch: typeof import('@components/auth-component/switch.vue').default;
    AuthTemplate: typeof import('@components/auth-component/component.vue').default;
    BkTable: typeof import('@blueking/table/typings/BkTable.vue');
    BkTableColumn: typeof import('@blueking/table/typings/BkTableColumn.vue');
    DbCard: typeof import('@components/db-card/index.vue').default;
    DbForm: typeof import('@components/db-form/index.vue').default;
    DbIcon: typeof import('@components/db-icon/index.ts').default;
    DbPopconfirm: typeof import('@components/db-popconfirm/index.vue').default;
    DbSearchSelect: typeof import('@components/db-search-select/index.vue').default;
    DbSideslider: typeof import('@components/db-sideslider/index.vue').default;
    DbStatus: typeof import('@components/db-status/index.vue').default;
    DbTable: typeof import('@components/db-table/Index.vue').default;
    EditableBlock: typeof import('@components/editable-table/Index.vue').Block;
    EditableColumn: typeof import('@components/editable-table/Index.vue').Column;
    EditableDatePicker: typeof import('@components/editable-table/Index.vue').DatePicker;
    EditableInput: typeof import('@components/editable-table/Index.vue').Input;
    EditableRow: typeof import('@components/editable-table/Index.vue').Row;
    EditableSelect: typeof import('@components/editable-table/Index.vue').Select;
    EditableTable: typeof import('@components/editable-table/Index.vue').default;
    EditableTagInput: typeof import('@components/editable-table/Index.vue').TagInput;
    EditableTextarea: typeof import('@components/editable-table/Index.vue').Textarea;
    EditableTimePicker: typeof import('@components/editable-table/Index.vue').TimePicker;
    FunController: typeof import('@components/function-controller/FunController.vue').default;
    MoreActionExtend: typeof import('@components/more-action-extend/Index.vue').default;
    OperationColumn: typeof import('@views/db-manage/common/toolbox-field/column/operation-column/Index.vue').default;
    ScrollFaker: typeof import('@components/scroll-faker/Index.vue').default;
    SmartAction: typeof import('@components/smart-action/Index.vue').default;
    TableDetailDialog: typeof import('@components/table-detail-dialog/Index.vue').default;
    // TTable: typeof import('@blueking/tdesign-ui').PrimaryTable;
    // TTableColumn: typeof import('@blueking/tdesign-ui').TableColumn;
  }
}

export {};
