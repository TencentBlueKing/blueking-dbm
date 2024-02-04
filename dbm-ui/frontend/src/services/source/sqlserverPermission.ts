
import SqlserverPermissionModel from '@services/model/sqlserver/sqlserver-permission';

//  type AccountTypesValues,
import { ConfLevels } from '@common/const';

const defalutList: SqlserverPermissionModel[] = [
  {
    account: {
      bk_biz_id: 3,
      user: 'aaron',
      creator: 'migrate',
      create_time: '2023-12-08T16:35:53Z',
      account_id: 123,
    },
    rules: [
      {
        account_id: 12128,
        bk_biz_id: 3,
        creator: 'migrate',
        create_time: '2023-12-08T16:35:53Z',
        rule_id: 125,
        access_db: 'db%',
        privilege: 'db_datawriter',
      },
      {
        account_id: 999,
        bk_biz_id: 3,
        creator: 'aszxc',
        create_time: '2024-01-04T07:38:09Z',
        rule_id: 191,
        access_db: 'tesdawdtuyy',
        privilege: 'create,alter,drop,index,execute,',
      },
    ],
    create_at: '2023-12-08T16:35:53Z',
    isNew: false,
  },
  {
    account: {
      bk_biz_id: 6,
      user: 'asdaw',
      creator: 'asdwaa',
      create_time: '2023-12-08T16:35:53Z',
      account_id: 128,
    },
    rules: [],
    create_at: '2024-02-04T16:35:53Z',
    isNew: false,
  },
];

const defalutRuleList = [
  {
    account: {
      bk_biz_id: 3,
      user: 'aaron',
      creator: 'migrate',
      create_time: '2023-12-08T16:35:53Z',
      account_id: 128,
    },
    rules: [
      // {
      //   account_id: 128,
      //   bk_biz_id: 3,
      //   creator: '',
      //   create_time: '2024-01-25T09:28:33Z',
      //   rule_id: 229,
      //   access_db: 'test',
      //   privilege: 'execute,create view',
      // },
    ],
  },
];

const requestSuccess = {
  code: 0,
  data: null,
  message: 'OK',
  request_id: '123',
};

const resourceTree = [
  {
    instance_name: 'randpass',
    instance_id: 91,
    obj_id: ConfLevels.APP,
    obj_name: 'CLUSTER',
    extra: {
      domain: 'sqlserver.randpass.dba.db',
      version: '7.10.2',
      proxy_version: '',
    },
  },
  {
    instance_name: 'asasd',
    instance_id: 91,
    obj_id: ConfLevels.MODULE,
    obj_name: 'CLUSTER',
    extra: {
      domain: 'sqlserver.asasd.dba.db',
      version: '7.10.2',
      proxy_version: '',
    },
  },
];

// 获取授权规则列表
export function getAccountRulesList() {
  return Promise.resolve(defalutList.map(item => new SqlserverPermissionModel(item)));
}

// 查询账号规则
export function queryAccountRules() {
  // payload: {
  // bizId: number,
  // user: string,
  // access_dbs: string[],
  // }
  return Promise.resolve(defalutRuleList);
}

// 添加账号规则
export function createAccountRule() {
  // payload: {
  // bizId: number,
  // access_db: string,
  // privilege: string[],
  // account_id: number
  // }
  return Promise.resolve(requestSuccess);
}

// 创建账户
export function createAccount() {
  //   payload: {
  //   password:string,
  //   user: string,
  //   account_type?: AccountTypesValues
  // }
  return Promise.resolve(requestSuccess);
}

// 删除账户
export function deleteAccount() {
  // account_id: number
  return Promise.resolve(requestSuccess);
}

/**
 * 获取业务拓扑树
 */
export function geSqlServerResourceTree() {
  return Promise.resolve(resourceTree);
}
