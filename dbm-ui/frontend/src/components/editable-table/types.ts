export interface IRule {
  required?: boolean;
  email?: boolean;
  min?: number;
  max?: number;
  maxlength?: number;
  pattern?: RegExp;
  validator?: (value: any) => Promise<boolean | string> | boolean | string;
  message: (() => string) | string;
  trigger: string;
}
