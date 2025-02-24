export interface IRule {
  email?: boolean;
  max?: number;
  maxlength?: number;
  message: (() => string) | string;
  min?: number;
  pattern?: RegExp;
  required?: boolean;
  trigger: string;
  validator?: (value: any, rowData?: Record<string, any>) => Promise<boolean | string> | boolean | string;
}
