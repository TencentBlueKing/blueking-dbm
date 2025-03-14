export interface IRule {
  email?: boolean;
  max?: number;
  maxlength?: number;
  message: (() => string) | string;
  min?: number;
  pattern?: RegExp;
  required?: boolean;
  trigger: string;
  validator?: (
    value: any,
    rowDataValue: {
      rowData: Record<string, any>;
      rowIndex: number;
    },
  ) => Promise<boolean | string> | boolean | string;
}
