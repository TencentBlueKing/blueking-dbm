<template>
  <div style="padding: 16px 24px">
    <BkTable
      class="openarea-create-table"
      :columns="columns"
      :data="tableData" />
  </div>
</template>
<script setup lang="tsx">
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { getPreview } from '@services/openarea';
  import { createTicket } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import { messageSuccess } from '@utils';

  interface Props {
    data: ServiceReturnType<typeof getPreview>,
    sourceClusterId: number
  }

  interface Expose{
    submit: () => Promise<any>
  }

  const props = defineProps<Props>();

  const router = useRouter();
  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const tableData = shallowRef<Array<{
    target_cluster_domain: string
  } & Props['data']['config_data'][0]['execute_objects'][0]>>([]);

  const columns = [
    {
      label: t('目标集群'),
      field: 'target_cluster_domain',
      showOverflowTooltip: true,
      width: 220,
    },
    {
      label: t('新 DB'),
      field: 'target_db',
      showOverflowTooltip: true,
    },
    {
      label: t('源 DB'),
      field: 'source_db',
      showOverflowTooltip: true,
    },
    {
      label: t('表结构'),
      showOverflowTooltip: true,
      render: ({ data }: {data: UnwrapRef<typeof tableData>[0]}) => (
        <>
          {data.schema_tblist.map(item => <bk-tag>{item}</bk-tag>)}
        </>
      ),
    },
    {
      label: t('表数据'),
      showOverflowTooltip: true,
      render: ({ data }: {data: UnwrapRef<typeof tableData>[0]}) => (
        <>
          {data.data_tblist.map(item => <bk-tag>{item}</bk-tag>)}
        </>
      ),
    },
    {
      label: t('授权 IP'),
      showOverflowTooltip: true,
      render: ({ data }: {data: UnwrapRef<typeof tableData>[0]}) => (
        <>
          {data.authorize_ips.map(item => (
            <bk-tag>{item}</bk-tag>
          ))}
        </>
      ),
    },
    {
      label: t('授权规则'),
      showOverflowTooltip: false,
      render: ({ data }: {data: UnwrapRef<typeof tableData>[0]}) => (
        <div class="rules-main">
          <bk-button
            text
            theme="primary">
            {t('n 条全新规则', { n: data.priv_data.length })}
          </bk-button>
          {data.error_msg && (
            <db-icon
              v-bk-tooltips={data.error_msg}
              class="error-icon"
              type="exclamation-fill" />
          )}
        </div>
      ),
    },
  ];

  watch(() => props.data, () => {
    if (!props.data) {
      return;
    }
    tableData.value = props.data.config_data.reduce((result, item) => {
      const [executeObjects] = item.execute_objects;
      result.push({
        target_cluster_domain: item.target_cluster_domain,
        ...executeObjects,
      });
      return result;
    }, [] as UnwrapRef<typeof tableData>);
  }, {
    immediate: true,
  });


  defineExpose<Expose>({
    submit() {
      if (tableData.value.some(item => item.error_msg)) {
        return Promise.resolve(false);
      }
      return createTicket({
        ticket_type: 'MYSQL_OPEN_AREA',
        remark: '',
        details: {
          force: false,
          cluster_id: props.sourceClusterId,
          ...props.data,
        },
        bk_biz_id: currentBizId,
      }).then(() => {
        messageSuccess(t('新建开区成功'));
        window.changeConfirm = false;
        router.push({
          name: 'mysqlOpenareaTemplate',
        });
      });
    },
  });
</script>
<<<<<<< HEAD
<style lang="less" scoped>
.openarea-create-table {
  :deep(.rules-main) {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;

    .error-icon {
      font-size: 14px;
      color: #ea3636;
      cursor: pointer;
    }
  }
}
</style>

=======
>>>>>>> c3acfbeaf (style(frontend): 使用prettier代码格式化 #3408)
