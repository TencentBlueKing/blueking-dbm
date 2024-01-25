<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->
<template>
  <div class="delete-nodes">
    <NodeNumber :id="data.id" />
    <BkAlert
      v-if="normalCount <= 3"
      theme="warning"
      :title="t('当前正常的节点数量少于n ，不能删除节点，请先添加节点', [3])" />
    <DbTable
      ref="tableRef"
      class="mt-16"
      :columns="columns"
      :data-source="getRiakNodeList"
      :is-row-select-enable="isRowSelectEnable" />
  </div>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import RiakModel from '@services/model/riak/riak';
  import RiakNodeModel from '@services/model/riak/riak-node';
  import { getRiakNodeList } from '@services/source/riak';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import RenderHostStatus from '@components/render-host-status/Index.vue';

  import { messageWarn } from '@utils';

  import NodeNumber from './components/NodeNumber.vue';

  interface Props {
    data: RiakModel
  }

  interface Emits {
    (e: 'submitSuccess'): void
  }

  interface Expose {
    submit: () => Promise<boolean>
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const columns = [
    {
      type: 'selection',
      minWidth: 48,
      width: 48,
    },
    {
      label: t('节点实例'),
      field: 'ip',
      render: ({ data }: { data: RiakNodeModel }) => <span>{ data.ip || '--' }</span>,
    },
    {
      label: t('Agent状态'),
      field: 'status',
      width: 100,
      render: ({ data }: { data: RiakNodeModel }) => <RenderHostStatus data={data.status} />,
    },
    {
      label: t('CPU内存'),
      field: 'cpu',
      render: ({ data }: { data: RiakNodeModel }) => <span>{ data.cpu || '--' }</span>,
    },
    {
      label: t('机型'),
      field: 'bk_host_name',
      render: ({ data }: { data: RiakNodeModel }) => <span>{ data.bk_host_name || '--' }</span>,
    },
  ];

  const tableRef = ref();

  const nodeList = computed<RiakNodeModel[]>(() => tableRef.value?.getData() || []);
  const normalCount = computed(() => nodeList.value.filter(nodeItem => nodeItem.isNodeNormal).length);

  const isRowSelectEnable = ({ row }: { row: RiakNodeModel }) => {
    if (normalCount.value > 3) {
      return row.isNodeNormal;
    }
    return false;
  };

  const fetchData = () => {
    tableRef.value.fetchData({}, {
      bk_biz_id: currentBizId,
      cluster_id: props.data.id,
    });
  };

  onMounted(() => {
    fetchData();
  });

  defineExpose<Expose>({
    submit() {
      return new Promise((resolve, reject) => {
        const params = {
          id: props.data.id,
          nodes: tableRef.value.bkTableRef.getSelection(),
        };

        if (params.nodes.length) {
          InfoBox({
            title: t('确认删除n个节点?', [params.nodes.length]),
            subTitle: (
              <>
                <p>
                  { t('节点IP') }：
                  {
                    params.nodes.map((riakNodeItem: RiakNodeModel) => <span>{ riakNodeItem.ip }</span>)
                  }
                </p>
                <p>{ t('删除后不可恢复，请谨慎操作！') }</p>
              </>
            ),
            confirmText: t('禁用'),
            cancelText: t('取消'),
            headerAlign: 'center',
            contentAlign: 'left',
            footerAlign: 'center',
            onConfirm: () => {
              createTicket({
                bk_biz_id: currentBizId,
                ticket_type: TicketTypes.RIAK_CLUSTER_SCALE_IN,
                details: {
                  cluster_id: props.data.id,
                  bk_cloud_id: props.data.bk_cloud_id,
                  nodes: tableRef.value.bkTableRef.getSelection().map((nodeItem: RiakNodeModel) => ({
                    ip: nodeItem.ip,
                    bk_host_id: nodeItem.bk_host_id,
                    bk_cloud_id: nodeItem.bk_cloud_id,
                    bk_biz_id: currentBizId,
                  })),
                },
              })
                .then((createTicketResult) => {
                  ticketMessage(createTicketResult.id);
                  emits('submitSuccess');
                  resolve(true);
                })
                .catch(() => reject());
            },
            onClosed: () => {
              reject();
            },
          });
        } else {
          messageWarn(t('请选择xx', [t('节点实例')]));
          reject();
        }
      });
    },
  });
</script>

<style lang="less" scoped>
.delete-nodes {
  padding: 0 40px 24px;
}
</style>
