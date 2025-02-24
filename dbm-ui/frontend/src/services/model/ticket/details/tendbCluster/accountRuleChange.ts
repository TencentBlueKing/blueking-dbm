import type { AccountRule, AccountRulePrivilege } from '@services/types/permission';

import type { DetailBase } from '../common';

export interface AccountRuleChange extends DetailBase {
  access_db: string;
  account_id: number;
  account_type: string;
  action: 'change' | 'delete';
  bk_biz_id: number;
  last_account_rules: {
    userName: string;
  } & AccountRule;
  privilege: AccountRulePrivilege;
  rule_id: number;
}
