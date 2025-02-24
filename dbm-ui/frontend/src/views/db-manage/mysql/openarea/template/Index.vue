<template>
  <div class="mysql-openarea-page">
    <BkAlert
      closable
      theme="info"
      :title="t('开区模板：通过开区模板，可以快速创建集群开区')" />
    <div class="header-action mt-16 mb-16">
      <AuthButton
        action-id="mysql_openarea_config_create"
        class="w-88"
        theme="primary"
        @click="handleGoCreate">
        {{ t('新建') }}
      </AuthButton>
      <BkInput
        v-model="searchKey"
        class="search-box"
        clearable
        :placeholder="t('请输入模板关键字')" />
    </div>
    <DbTable
      ref="tableRef"
      :columns="tableColumns"
      :data-source="getList"
      @column-sort="columnSortChange" />
  </div>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import OpenareaTemplateModel from '@services/model/openarea/openareaTemplate';
  import { getList, remove } from '@services/source/openarea';

  import { useDebouncedRef, useTicketCloneInfo } from '@hooks';

  import { TicketTypes } from '@common/const';

  import { messageSuccess } from '@utils';

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const tableRef = ref();
  const searchKey = useDebouncedRef(route.query.config_name as string);

  // 单据克隆
  useTicketCloneInfo({
    onSuccess(cloneData) {
      router.push({
        name: 'mysqlOpenareaCreate',
        params: {
          id: cloneData.id,
        },
        query: {
          from: route.name as string,
          ticketId: route.query.ticketId,
        },
      });
    },
    type: TicketTypes.MYSQL_OPEN_AREA,
  });

  const tableColumns = [
    {
      field: 'config_name',
      label: t('模板名称'),
    },
    {
      field: 'cluster_type',
      label: t('类型'),
      render: ({ data }: { data: OpenareaTemplateModel }) =>
        data.cluster_type === 'tendbha' ? t('主从') : t('单节点'),
    },
    {
      field: 'config_name',
      label: t('源集群'),
      render: ({ data }: { data: OpenareaTemplateModel }) => data.source_cluster.immute_domain || '--',
    },
    {
      field: 'updater',
      label: t('更新人'),
    },
    {
      field: 'update_at',
      label: t('更新时间'),
      render: ({ data }: { data: OpenareaTemplateModel }) => data.updateAtDisplay || '--',
      sort: true,
    },
    {
      label: t('操作'),
      render: ({ data }: { data: OpenareaTemplateModel }) => (
        <>
          <router-link
            to={{
              name: 'mysqlOpenareaCreate',
              params: {
                id: data.id,
              },
              query: {
                from: route.name,
              },
            }}>
            {t('开区')}
          </router-link>
          <auth-router-link
            to={{
              name: 'MySQLOpenareaTemplateEdit',
              params: {
                id: data.id,
              },
              query: {
                from: route.name,
              },
            }}
            action-id='mysql_openarea_config_update'
            class='ml-16'
            permission={data.permission.mysql_openarea_config_update}
            resource={data.id}>
            {t('编辑')}
          </auth-router-link>
          <auth-template
            action-id='mysql_openarea_config_destroy'
            permission={data.permission.mysql_openarea_config_destroy}
            resource={data.id}>
            <db-popconfirm
              confirmHandler={() => handleRemove(data)}
              content={t('删除操作无法撤回，请谨慎操作！')}
              title={t('确认删除该模板？')}>
              <bk-button
                class='ml-16'
                theme='primary'
                text>
                {t('删除')}
              </bk-button>
            </db-popconfirm>
          </auth-template>
        </>
      ),
      width: 190,
    },
  ];

  watch(searchKey, () => {
    nextTick(() => {
      tableRef.value.fetchData(
        {
          config_name: searchKey.value,
        },
        {
          cluster_type: 'tendbha,tendbsingle',
        },
      );
    });
  });

  const fetchData = () => {
    tableRef.value.fetchData(
      {},
      {
        cluster_type: 'tendbha,tendbsingle',
      },
    );
  };

  // 表头排序
  const columnSortChange = (data: {
    column: {
      field: string;
      label: string;
    };
    index: number;
    type: 'asc' | 'desc' | 'null';
  }) => {
    let desc = '';
    if (data.type === 'asc') {
      desc = data.column.field;
    } else if (data.type === 'desc') {
      desc = `-${data.column.field}`;
    }
    tableRef.value.fetchData({
      cluster_type: 'tendbha,tendbsingle',
      desc,
    });
  };

  const handleGoCreate = () => {
    router.push({
      name: 'MySQLOpenareaTemplateCreate',
    });
  };

  const handleRemove = (data: OpenareaTemplateModel) =>
    remove(data).then(() => {
      messageSuccess(t('删除成功'));
      fetchData();
    });

  onMounted(() => {
    fetchData();
  });
</script>
<style lang="less">
  .mysql-openarea-page {
    .header-action {
      display: flex;

      .search-box {
        width: 390px;
        margin-left: auto;
      }
    }
  }
</style>
