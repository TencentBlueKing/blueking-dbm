<template>
  <div class="spider-openarea-page">
    <BkAlert
      closable
      theme="info"
      :title="t('开区模板：通过开区模板，可以快速创建集群开区')" />
    <div class="header-action mt-16 mb-16">
      <AuthButton
        action-id="tendb_openarea_config_create"
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
  import {
    onMounted,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import OpenareaTemplateModel from '@services/model/openarea/openareaTemplate';
  import {
    getList,
    remove,
  } from '@services/source/openarea';

  import { useDebouncedRef,useTicketCloneInfo  } from '@hooks';

  import { TicketTypes } from '@common/const';

  import { messageSuccess } from '@utils';


  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();
  const searchKey = useDebouncedRef(route.query.config_name as string);

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.TENDBCLUSTER_OPEN_AREA,
    onSuccess(cloneData) {
      router.push({
        name: 'spiderOpenareaCreate',
        params: {
          id: cloneData.id,
        },
        query: {
          from: route.name as string
        }
      })
    },
  });

  const tableRef = ref();

  const tableColumns = [
    {
      label: t('模板名称'),
      field: 'config_name',
    },
    {
      label: t('源集群'),
      field: 'config_name',
      render: ({ data }: {data: OpenareaTemplateModel}) => data.source_cluster.immute_domain || '--',
    },
    {
      label: t('更新人'),
      field: 'updater',
    },
    {
      label: t('更新时间'),
      field: 'update_at',
      sort: true,
      render: ({ data }: {data: OpenareaTemplateModel}) => data.updateAtDisplay || '--',
    },
    {
      label: t('操作'),
      width: 190,
      render: ({ data }: {data: OpenareaTemplateModel}) => (
        <>
          <router-link
            to={{
              name: 'spiderOpenareaCreate',
              params: {
                id: data.id,
              },
              query: {
                from: route.name
              }
            }}>
            { t('开区') }
          </router-link>
          <auth-router-link
            action-id="tendb_openarea_config_update"
            resource={data.id}
            permission={data.permission.tendb_openarea_config_update}
            class="ml-16"
            to={{
              name: 'spiderOpenareaTemplateEdit',
              params: {
                id: data.id,
              },
              query: {
                from: route.name
              }
            }}>
            { t('编辑') }
          </auth-router-link>
          <auth-template
            action-id="tendb_openarea_config_destroy"
            resource={data.id}
            permission={data.permission.tendb_openarea_config_destroy}>
            <db-popconfirm
              title={t('确认删除该模板？')}
              content={t('删除操作无法撤回，请谨慎操作！')}
              confirmHandler={() => handleRemove(data)}>
              <bk-button
                class="ml-16"
                text
                theme="primary">
                { t('删除') }
              </bk-button>
            </db-popconfirm>
          </auth-template>
        </>
      ),
    },
  ];

  watch(
    searchKey,
    () => {
      nextTick(() => {
        tableRef.value.fetchData({
          config_name: searchKey.value,
        }, {
          cluster_type: 'tendbcluster',
        });
      })
    }
  );

  const fetchData = () => {
    tableRef.value.fetchData({}, {
      cluster_type: 'tendbcluster',
    });
  };

  // 表头排序
  const columnSortChange = (data: {
    column: {
      field: string;
      label: string;
    };
    index: number;
    type: 'asc' | 'desc' | 'null'
  }) => {
    let desc = ''
    if (data.type === 'asc') {
      desc = data.column.field;
    } else if (data.type === 'desc') {
      desc = `-${data.column.field}`;
    }
    tableRef.value.fetchData({
      desc,
      cluster_type: 'tendbcluster',
    });
  };

  const handleGoCreate = () => {
    router.push({
      name: 'spiderOpenareaTemplateCreate',
    });
  };

  const handleRemove = (data: OpenareaTemplateModel) => remove(data).then(() => {
    messageSuccess(t('删除成功'));
    fetchData();
  });

  onMounted(() => {
    fetchData();
  });
</script>
<style lang="less">
  .spider-openarea-page {
    .header-action {
      display: flex;

      .search-box {
        width: 390px;
        margin-left: auto;
      }
    }
  }
</style>
