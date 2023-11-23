<template>
  <div class="spider-openarea-page">
    <BkAlert
      closable
      theme="info"
      :title="t('开区模板：通过开区模板，可以快速创建集群开区')" />
    <div class="header-action mt-16 mb-16">
      <BkButton
        class="w-88"
        theme="primary"
        @click="handleGoCreate">
        {{ t('新建') }}
      </BkButton>
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
  import {
    onMounted,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import OpenareaTemplateModel from '@services/model/openarea/openareaTemplate';
  import {
    getList,
    remove,
  } from '@services/openarea';

  import { useDebouncedRef } from '@hooks';

  import { messageSuccess } from '@utils';


  const { t } = useI18n();
  const router = useRouter();

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
      render: ({ data }: {data: OpenareaTemplateModel}) => (
        data.source_cluster.immute_domain || '--'
      ),
    },
    {
      label: t('更新人'),
      render: ({ data }: {data: OpenareaTemplateModel}) => (
        data.updater || '--'
      ),
    },
    {
      label: t('更新时间'),
      render: ({ data }: {data: OpenareaTemplateModel}) => (
        data.update_at || '--'
      ),
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
              }}>
              { t('开区') }
            </router-link>
            <router-link
              class="ml-16"
              to={{
                name: 'spiderOpenareaTemplateEdit',
                params: {
                  id: data.id,
                },
              }}>
              { t('编辑') }
            </router-link>
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
          </>
        ),
    },
  ];

  const fetchData = () => {
    tableRef.value.fetchData();
  };

  watch(serachKey, () => {
    tableRef.value.fetchData({
      config_name: serachKey.value,
    });
  });

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
    .header-action{
      display: flex;

      .search-box{
        width: 390px;
        margin-left: auto;
      }
    }
  }
</style>
