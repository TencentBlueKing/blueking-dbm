import type { AccountRule, AccountRulePrivilege } from '@services/types/permission';

import type { DetailBase } from '../common';
/**
 * MySQL 权限规则变更
 */
export interface AccountRuleChange extends DetailBase {
  last_account_rules: AccountRule & {
    userName: string;
  };
  action: 'change' | 'delete';
  account_id: number;
  access_db: string;
  privilege: AccountRulePrivilege;
  bk_biz_id: number;
  account_type: string;
  rule_id: number;
}
