<template>
  <div class="mt-16 mb-24">
    <PrimaryTable
      :columns="columns"
      :data="tableData"
      :max-height="tableMaxHeight"
      row-key="rowKey"
      :rowspan-and-colspan="rowspanAndColspan">
      <template #empty>
        <EmptyStatus
          :is-anomalies="false"
          :is-searching="false" />
      </template>
    </PrimaryTable>
    <div class="table-footer">
      <BkPagination
        v-bind="pagination"
        :model-value="pagination.current"
        @change="handleTableValueChange"
        @limit-change="handleTableLimitChange" />
    </div>
  </div>
</template>

<script setup lang="tsx">
  import type { PrimaryTableCol, PrimaryTableProps } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import { getAccountPrivs } from '@services/source/mysqlPermissionAccount';

  import { useTableMaxHeight } from '@hooks';

  import { AccountTypes } from '@common/const';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import { isSensitivePriv } from './common/utils';

  interface TableItem {
    db: string[];
    immute_domain: string;
    ip: string[];
    match_db: string;
    match_ip: string;
    priv: string;
    rowKey: string;
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

  const columns = computed<PrimaryTableCol[]>(() => {
    const domainColumns: PrimaryTableCol[] = [
      {
        children: [
          {
            cell: (_, { row }) => (
              <>
                {props.options?.is_master ? (
                  <bk-tag theme='info'>{t('主')}</bk-tag>
                ) : (
                  <bk-tag theme='success'>{t('从')}</bk-tag>
                )}
                <span class='ml-4'>{(row as TableItem).immute_domain}</span>
              </>
            ),
            colKey: 'immute_domain',
            title: t('集群域名'),
            width: 240,
          },
          {
            colKey: 'user',
            title: t('账号'),
            width: 240,
          },
          {
            colKey: 'match_ip',
            title: t('匹配中的访问源'),
            width: 240,
          },
          {
            cell: (_, { row }) => <bk-tag>{(row as TableItem).match_db}</bk-tag>,
            colKey: 'match_db',
            title: t('匹配中的 DB'),
            width: 240,
          },
          {
            cell: (_, { row }) => {
              const { priv } = row as TableItem;
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
            colKey: 'priv',
            title: t('权限'),
            width: 240,
          },
        ],
        title: t('匹配的规则'),
      },
      {
        children: [
          {
            cell: (_, { row }) => <span style='font-weight: bolder'>{(row as TableItem).ip.join('，')}</span>,
            colKey: 'ip',
            title: t('源客户端 IP'),
            width: 240,
          },
        ],
        title: t('查询的对象 IP'),
      },
    ];

    if (props.options?.dbs) {
      domainColumns[1]!.children!.push({
        cell: (_, { row }) => (row as TableItem).db.map((dbItem) => <bk-tag>{dbItem}</bk-tag>),
        colKey: 'db',
        title: t('访问的 DB'),
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
                rowKey: `${acc.length}`,
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

  const rowspanPredicateMap: Record<string, (item: TableItem, row: TableItem) => boolean> = {
    immute_domain: (item, row) => item.immute_domain === row.immute_domain,
    ip: (item, row) => item.ip === row.ip,
    match_ip: (item, row) =>
      item.immute_domain === row.immute_domain && item.user === row.user && item.match_ip === row.match_ip,
    user: (item, row) => item.immute_domain === row.immute_domain && item.user === row.user,
  };

  const rowspanAndColspan: PrimaryTableProps['rowspanAndColspan'] = ({ col, row, rowIndex }) => {
    const predicate = rowspanPredicateMap[col.colKey as string];
    if (!predicate) {
      return {};
    }
    const rowData = row as TableItem;
    // 合并行只在分组首行声明 rowspan，其余行由 tdesign 自动跳过
    if (tableData.value.findIndex((item) => predicate(item, rowData)) !== rowIndex) {
      return {};
    }
    const rowSpan = tableData.value.filter((item) => predicate(item, rowData)).length;
    return rowSpan > 1 ? { rowspan: rowSpan } : {};
  };

  const handleTableLimitChange = (value: number) => {
    emits('page-limit-change', value);
  };

  const handleTableValueChange = (value: number) => {
    emits('page-value-change', value);
  };
</script>

<style lang="less" scoped>
  .table-footer {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
  }
</style>
