<template>
  <div style="padding: 16px 24px">
    <BkTable
      class="openarea-create-table"
      :columns="columns"
      :data="tableData" />
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import type { UnwrapRef } from 'vue';
  import {
    shallowRef,
    watch
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { getPreview } from '@services/source/openarea';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import RenderTagOverflow from '@components/render-tag-overflow/Index.vue'

  import { messageError } from '@utils';

  interface Props {
    data: ServiceReturnType<typeof getPreview>,
    sourceClusterId: number
  }

  interface Expose{
    submit: () => Promise<any>
  }

  type RowData = UnwrapRef<typeof tableData>[0];

  const props = defineProps<Props>();

  const router = useRouter();
  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const tableData = shallowRef<Array<{
    target_cluster_domain: string
  } & Props['data']['config_data'][0]['execute_objects'][0]>>([]);

  const columns = computed(() => [
    {
      label: t('目标集群'),
      field: 'target_cluster_domain',
      showOverflowTooltip: true,
      width: 280,
      rowspan: ({ row }: { row: RowData }) => {
        const rowSpan = tableData.value.filter(item => item.target_cluster_domain === row.target_cluster_domain).length;
        return rowSpan > 1 ? rowSpan : 1;
      },
    },
    {
      label: t('新 DB'),
      field: 'target_db',
      showOverflowTooltip: true,
      width: 230,
    },
    {
      label: t('表结构'),
      showOverflowTooltip: true,
      width: 80,
      render: () => t('所有表'),
    },
    {
      label: t('表数据'),
      showOverflowTooltip: true,
      width: 300,
      render: ({ data }: {data: RowData}) => <RenderTagOverflow data={_.flatMap(data.data_tblist)} />,
    },
    {
      label: t('授权 IP'),
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => data.authorize_ips.join(','),
    },
  ]);

  watch(() => props.data, () => {
    if (!props.data) {
      return;
    }
    tableData.value = props.data.config_data.reduce((result, item) => {
      item.execute_objects.forEach(executeObjects => {
        result.push({
          target_cluster_domain: item.target_cluster_domain,
          ...executeObjects,
        });
      })
      return result;
    }, [] as RowData[]);
  }, {
    immediate: true,
  });

  defineExpose<Expose>({
    submit() {
      const errorRow = tableData.value.find(item => item.error_msg);
      if (errorRow) {
        messageError(errorRow.error_msg);
        return Promise.resolve(false);
      }

      return createTicket({
        ticket_type: 'TENDBCLUSTER_OPEN_AREA',
        remark: '',
        details: {
          force: false,
          cluster_id: props.sourceClusterId,
          ...props.data,
        },
        bk_biz_id: currentBizId,
      }).then((data) => {
        ticketMessage(data.id);
        window.changeConfirm = false;
        router.push({
          name: 'spiderOpenareaTemplate',
        });
      });
    },
  });
</script>
