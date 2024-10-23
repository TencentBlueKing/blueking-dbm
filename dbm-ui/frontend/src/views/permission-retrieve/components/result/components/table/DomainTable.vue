<template>
  <DbOriginalTable
    class="mt-16 mb-24"
    :columns="columns"
    :data="tableData"
    :max-height="tableMaxHeight"
    :pagination="pagination"
    remote-pagination
    @page-limit-change="handleTableLimitChange"
    @page-value-change="handleTableValueChange" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getAccountPrivs } from '@services/source/mysqlPermissionAccount';

  import { AccountTypes } from '@common/const';

  import { isSensitivePriv } from './common/utils'

  interface TableItem {
    ip: string[],
    db: string[],
    immute_domain: string,
    user: string,
    match_ip: string,
    match_db: string,
    priv: string
  }

  interface Props {
    data?: ServiceReturnType<typeof getAccountPrivs>;
    isMaster: boolean;
    dbMemo: string[];
    tableMaxHeight: number;
    pagination: {
      current: number,
      count: number,
      limit: number,
      limitList: number[],
    }
  }

  interface Emits {
    (e: 'page-limit-change'): void;
    (e: 'page-value-change'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const route = useRoute()

  const { accountType } = route.meta as { accountType: AccountTypes };

  const columns = computed(() => {
    const domainColumns = [
      {
        label: t('匹配的规则'),
        children: [
          {
            label: t('集群域名'),
            field: 'immute_domain',
            width: 240,
            rowspan: ({ row }: { row: TableItem }) => {
              const rowSpan = tableData.value.filter((item) => item.immute_domain === row.immute_domain).length;
              return rowSpan > 1 ? rowSpan : 1;
            },
            render: ({ row }: { row: TableItem }) => (
              <>
                {
                  props.isMaster ? <bk-tag theme="info">{t('主')}</bk-tag> : <bk-tag theme="success">{t('从')}</bk-tag>
                }
                <span class="ml-4">{row.immute_domain}</span>
              </>
            ),
          },
          {
            label: t('账号'),
            field: 'user',
            width: 240,
            rowspan: ({ row }: { row: TableItem }) => {
              const rowSpan = tableData.value.filter((item) => item.immute_domain === row.immute_domain).length;
              return rowSpan > 1 ? rowSpan : 1;
            },
          },
          {
            label: t('匹配中的访问源'),
            field: 'match_ip',
            width: 240,
            rowspan: ({ row }: { row: TableItem }) => {
              const rowSpan = tableData.value.filter((item) => item.immute_domain === row.immute_domain && item.match_ip === row.match_ip).length;
              return rowSpan > 1 ? rowSpan : 1;
            },
          },
          {
            label: t('匹配中的 DB'),
            field: 'match_db',
            width: 240,
            render: ({ row }: { row: TableItem }) => <bk-tag>{row.match_db}</bk-tag>
          },
          {
            label: t('权限'),
            field: 'priv',
            width: 240,
            render: ({ row }: { row: TableItem }) => {
              const { priv } = row
              const privList = priv.split(',')

              return privList.map((privItem, index) => (
                <>
                  { index !== 0 && <span>，</span> }
                  <span>{privItem}</span>
                  { isSensitivePriv(accountType, privItem) && (
                    <bk-tag
                      size="small"
                      theme="warning"
                      class="ml-4"
                    >
                      {t('敏感')}
                    </bk-tag>
                  )}
                </>
              ))
            }
          },
        ]
      },
      {
        label: t('查询的对象 IP'),
        children: [
          {
            label: t('源客户端 IP'),
            field: 'ip',
            width: 240,
            rowspan: ({ row }: { row: TableItem }) => {
              const rowSpan = tableData.value.filter((item) => item.ip === row.ip).length;
              return rowSpan > 1 ? rowSpan : 1;
            },
            render: ({ row }: { row: TableItem }) => <span style="font-weight: bolder">{row.ip.join('，')}</span>,
          },
        ]
      }
    ];

    if (props.dbMemo.length > 0) {
      domainColumns[1].children.push({
        label: t('访问的 DB'),
        field: 'db',
        width: 240,
        render: ({ row }: { row: TableItem }) => row.db.map(dbItem => <bk-tag>{dbItem}</bk-tag>)
      })
    }

    return domainColumns;
  });

  const tableData = computed(() => {
    const {data} = props
    if (data && data.results.privs_for_cluster) {
        const privsForCluster = data.results.privs_for_cluster;
        const result = privsForCluster.reduce<TableItem[]>((acc, ipItem) => acc.concat(
          ipItem.users.reduce<TableItem[]>((userAcc, userItem) => userAcc.concat(
            userItem.match_ips.reduce<TableItem[]>((matchIpAcc, matchIpItem) => matchIpAcc.concat(
              matchIpItem.match_dbs.map(matchDbItem => {
                const ipDb = matchDbItem.ip_dbs.reduce<{
                  ip: string[],
                  db: string[]
                }>((prevIpDb, ipDbItem) => ({
                  ip: prevIpDb.ip.concat(ipDbItem.ip),
                  db: prevIpDb.ip.concat(ipDbItem.db)
                }), {
                  ip: [],
                  db: []
                });

                return {
                  immute_domain: ipItem.immute_domain,
                  user: userItem.user,
                  match_ip: matchIpItem.match_ip,
                  match_db: matchDbItem.match_db,
                  priv: matchDbItem.priv.toLocaleLowerCase(),
                  ...ipDb
                }
              })
            ), [])
          ), [])
        ), []);
        return result
      }
    return [];
  });

  const handleTableLimitChange = () => {
    emits('page-limit-change')
  }

  const handleTableValueChange = () => {
    emits('page-value-change')
  }
</script>
