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

  import { useTableMaxHeight } from '@hooks';

  import { AccountTypes } from '@common/const';

  import { isSensitivePriv } from './common/utils';

  interface TableItem {
    db: string[];
    immute_domain: string;
    ip: string[];
    match_db: string;
    match_ip: string;
    priv: string;
    user: string;
  }

  interface Props {
    data?: ServiceReturnType<typeof getAccountPrivs>;
    options?: {
      account_type: AccountTypes;
      dbs?: string;
      is_master?: boolean;
    };
    pagination: {
      count: number;
      current: number;
      limit: number;
      limitList: number[];
    };
  }

  interface Emits {
    (e: 'page-limit-change', value: number): void;
    (e: 'page-value-change', value: number): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const tableMaxHeight = useTableMaxHeight(530);

  const columns = computed(() => {
    const domainColumns = [
      {
        children: [
          {
            field: 'immute_domain',
            label: t('集群域名'),
            render: ({ row }: { row: TableItem }) => (
              <>
                {props.options?.is_master ? (
                  <bk-tag theme='info'>{t('主')}</bk-tag>
                ) : (
                  <bk-tag theme='success'>{t('从')}</bk-tag>
                )}
                <span class='ml-4'>{row.immute_domain}</span>
              </>
            ),
            rowspan: ({ row }: { row: TableItem }) => {
              const rowSpan = tableData.value.filter((item) => item.immute_domain === row.immute_domain).length;
              return rowSpan > 1 ? rowSpan : 1;
            },
            width: 240,
          },
          {
            field: 'user',
            label: t('账号'),
            rowspan: ({ row }: { row: TableItem }) => {
              const rowSpan = tableData.value.filter(
                (item) => item.immute_domain === row.immute_domain && item.user === row.user,
              ).length;
              return rowSpan > 1 ? rowSpan : 1;
            },
            width: 240,
          },
          {
            field: 'match_ip',
            label: t('匹配中的访问源'),
            rowspan: ({ row }: { row: TableItem }) => {
              const rowSpan = tableData.value.filter(
                (item) =>
                  item.immute_domain === row.immute_domain && item.user === row.user && item.match_ip === row.match_ip,
              ).length;
              return rowSpan > 1 ? rowSpan : 1;
            },
            width: 240,
          },
          {
            field: 'match_db',
            label: t('匹配中的 DB'),
            render: ({ row }: { row: TableItem }) => <bk-tag>{row.match_db}</bk-tag>,
            width: 240,
          },
          {
            field: 'priv',
            label: t('权限'),
            render: ({ row }: { row: TableItem }) => {
              const { priv } = row;
              const privList = priv.split(',');

              return privList.map((privItem, index) => (
                <>
                  {index !== 0 && <span>，</span>}
                  <span>{privItem}</span>
                  {isSensitivePriv(props.options?.account_type || AccountTypes.MYSQL, privItem) && (
                    <bk-tag
                      class='ml-4'
                      size='small'
                      theme='warning'>
                      {t('敏感')}
                    </bk-tag>
                  )}
                </>
              ));
            },
            width: 240,
          },
        ],
        label: t('匹配的规则'),
      },
      {
        children: [
          {
            field: 'ip',
            label: t('源客户端 IP'),
            render: ({ row }: { row: TableItem }) => <span style='font-weight: bolder'>{row.ip.join('，')}</span>,
            rowspan: ({ row }: { row: TableItem }) => {
              const rowSpan = tableData.value.filter((item) => item.ip === row.ip).length;
              return rowSpan > 1 ? rowSpan : 1;
            },
            width: 240,
          },
        ],
        label: t('查询的对象 IP'),
      },
    ];

    if (props.options?.dbs) {
      domainColumns[1].children.push({
        field: 'db',
        label: t('访问的 DB'),
        render: ({ row }: { row: TableItem }) => row.db.map((dbItem) => <bk-tag>{dbItem}</bk-tag>),
        width: 240,
      });
    }

    return domainColumns;
  });

  const tableData = computed(() => {
    const { data } = props;
    if (data && data.results.privs_for_cluster) {
      const privsForCluster = data.results.privs_for_cluster;
      return privsForCluster.reduce<TableItem[]>((acc, ipItem) => {
        ipItem.users.forEach((userItem) => {
          userItem.match_ips.forEach((matchIpItem) => {
            matchIpItem.match_dbs.forEach(({ ip_dbs: ipDbs, priv, ...rest }) => {
              const ip = [];
              const db = [];
              for (const { db: dbVal, ip: ipVal } of ipDbs) {
                ip.push(ipVal);
                db.push(dbVal);
              }
              acc.push({
                db,
                immute_domain: ipItem.immute_domain,
                ip,
                match_ip: matchIpItem.match_ip,
                priv: priv.toLocaleLowerCase(),
                user: userItem.user,
                ...rest,
              });
            });
          });
        });
        return acc;
      }, []);
    }

    return [];
  });

  const handleTableLimitChange = (value: number) => {
    emits('page-limit-change', value);
  };

  const handleTableValueChange = (value: number) => {
    emits('page-value-change', value);
  };
</script>
