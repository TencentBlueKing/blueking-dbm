declare module 'vue' {
  interface GlobalComponents {
    AuthButton: typeof import('@components/auth-component/button.vue').default;
    AuthOption: typeof import('@components/auth-component/option.vue').default;
    AuthRouterLink: typeof import('@components/auth-component/router-link.vue').default;
    AuthSwitcher: typeof import('@components/auth-component/switch.vue').default;
    AuthTemplate: typeof import('@components/auth-component/component.vue').default;
    DbCard: typeof import('@components/db-card/index.vue').default;
    DbDateTimePicker: typeof import('@components/db-date-time-picker/Index.vue').default;
    DbForm: typeof import('@components/db-form/index.vue').default;
    DbFormItem: typeof import('@components/db-form/item.vue').default;
    DbIcon: typeof import('@components/db-icon/index.ts').default;
    DbInput: typeof import('@components/bkui-vue/input/Index.vue').default;
    DbPopconfirm: typeof import('@components/db-popconfirm/index.vue').default;
    DbQuickSearch: typeof import('@components/db-quick-search/Index.vue').default;
    DbResetButton: typeof import('@components/db-reset-button/index.vue').default;
    DbSearchSelect: typeof import('@components/db-search-select/index.vue').default;
    DbSideslider: typeof import('@components/db-sideslider/index.vue').default;
    DbStatus: typeof import('@components/db-status/index.vue').default;
    DbTag: typeof import('@components/bkui-vue/tag/Index.vue').default;
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
    NewFeatureGuide: typeof import('@components/new-feature-guide/Index.vue').default;
    OperationColumn: typeof import('@views/db-manage/common/toolbox-field/column/operation-column/Index.vue').default;
    PrimaryTable: typeof import('@components/tdesign-ui/table').PrimaryTable;
    ScrollFaker: typeof import('@components/scroll-faker/Index.vue').default;
    SmartAction: typeof import('@components/smart-action/Index.vue').default;
    TableColumn: typeof import('@components/tdesign-ui/table').TableColumn;
    TableDetailDialog: typeof import('@components/table-detail-dialog/Index.vue').default;
    TicketInfoTable: typeof import('@views/ticket-center/common/ticket-detail/components/common/info-table/Index.vue').default;
    TicketInfoTableColumn: typeof import('@views/ticket-center/common/ticket-detail/components/common/info-table/Index.vue').InfoTableColumn;
  }
}

export {};
