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
        v-model="serachKey"
        class="search-box"
        :placeholder="t('请输入模板关键字')" />
    </div>
    <DbTable
      ref="tableRef"
      :columns="tableColumns"
      :data-source="getList" />
  </div>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import OpenareaTemplateModel from '@services/model/openarea/openareaTemplate';
  import {
    getList,
    remove,
  } from '@services/openarea';

  import { useDebouncedRef } from '@hooks';

  import { messageSuccess } from '@utils';

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const tableRef = ref();
  const serachKey = useDebouncedRef('');

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
      render: ({ data }: {data: OpenareaTemplateModel}) => data.updateAtDisplay || '--',
    },
    {
      label: t('操作'),
      width: 190,
      render: ({ data }: {data: OpenareaTemplateModel}) => (
        <>
          <router-link
            to={{
              name: 'mysqlOpenareaCreate',
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
            action-id="mysql_openarea_config_update"
            resource={data.id}
            permission={data.permission.mysql_openarea_config_update}
            class="ml-16"
            to={{
              name: 'mysqlOpenareaTemplateEdit',
              params: {
                id: data.id,
              },
              query: {
                from: route.name
              }
            }}>
            { t('编辑') }
          </auth-router-link>
          <db-popconfirm
            title={t('确认删除该模板？')}
            content={t('删除操作无法撤回，请谨慎操作！')}
            confirmHandler={() => handleRemove(data)}>
            <auth-button
              action-id="mysql_openarea_config_destroy"
              resource={data.id}
              permission={data.permission.mysql_openarea_config_destroy}
              class="ml-16"
              text
              theme="primary">
              { t('删除') }
            </auth-button>
          </db-popconfirm>
        </>
      ),
    },
  ];

  const fetchData = () => {
    tableRef.value.fetchData({
      cluster_type: 'tendbha',
    });
  };

  watch(serachKey, () => {
    tableRef.value.fetchData({
      config_name: serachKey.value,
    });
  });

  const handleGoCreate = () => {
    router.push({
      name: 'mysqlOpenareaTemplateCreate',
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
