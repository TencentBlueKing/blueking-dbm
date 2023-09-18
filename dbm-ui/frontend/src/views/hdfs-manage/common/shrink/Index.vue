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
  <div class="hdfs-cluster-shrink-box">
    <DbForm
      form-type="vertical"
      :model="formData">
      <DbFormItem label="">
        <div>
          <BkButton @click="handleShowListNode">
            {{ $t('添加节点IP') }}
          </BkButton>
          <I18nT
            keypath="已选n台主机"
            style="padding-left: 13px; color: #313238;"
            tag="span">
            <template #n>
              <span style="padding: 0 4px;font-weight: bold;color: #3a84ff;">
                {{ formData.selectNodeList.length }}
              </span>
            </template>
          </I18nT>
        </div>
        <DbOriginalTable
          class="mt16"
          :columns="columns"
          :data="formData.selectNodeList" />
      </DbFormItem>
      <DbFormItem :label="$t('备注')">
        <BkInput
          v-model="formData.remark"
          :maxlength="100"
          :placeholder="$t('请提供更多有用信息申请信息_以获得更快审批')"
          type="textarea" />
      </DbFormItem>
    </DbForm>
    <ListNode
      v-model="formData.selectNodeList"
      v-model:is-show="isShowListNode"
      :cluster-id="clusterId"
      from="shrink" />
  </div>
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import {
    reactive,
    ref,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type HdfsNodeModel from '@services/model/hdfs/hdfs-node';
  import { createTicket } from '@services/ticket';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { messageError } from '@utils';

  import ListNode from '../common/ListNode.vue';

  interface Props {
    clusterId: number,
    nodeList: Array<HdfsNodeModel>
  }

  interface Emits {
    (e: 'change'): void
  }

  interface Exposes {
    submit: () => Promise<any>,
    cancel: () => Promise<any>,
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const globalBizsStore = useGlobalBizs();
  const ticketMessage = useTicketMessage();
  const { t } = useI18n();

  const columns = [
    {
      label: t('节点IP'),
      field: 'ip',
    },
    {
      label: t('实例数量'),
      field: 'node_count',
    },
    {
      label: t('Agent状态'),
      field: 'status',
    },
    {
      label: t('操作'),
      width: 80,
      render: ({ data }: {data: HdfsNodeModel}) => (
        <>
          <bk-button
            theme="primary"
            text
            onClick={() => handleRemove(data)}>
            { t('移除') }
          </bk-button>
        </>
      ),
    },
  ];
  const isShowListNode = ref(false);
  const formData = reactive({
    selectNodeList: [] as Array<HdfsNodeModel>,
    remark: '',
  });

  watch(() => props.nodeList, () => {
    formData.selectNodeList = [...props.nodeList];
  }, {
    immediate: true,
  });

  const handleShowListNode = () => {
    isShowListNode.value = true;
  };

  const handleRemove = (data: HdfsNodeModel) => {
    formData.selectNodeList = formData.selectNodeList.reduce((result, item) => {
      if (item.bk_host_id !== data.bk_host_id) {
        result.push(item);
      }
      return result;
    }, [] as Array<HdfsNodeModel>);
  };

  defineExpose<Exposes>({
    submit() {
      return new Promise((resolve, reject) => {
        if (formData.selectNodeList.length < 1) {
          messageError(t('缩容节点不能为空'));
          return reject();
        }
        InfoBox({
          title: t('确认缩容集群'),
          subTitle: '',
          confirmText: t('确认'),
          cancelText: t('取消'),
          headerAlign: 'center',
          contentAlign: 'center',
          footerAlign: 'center',
          onClosed: () => reject(),
          onConfirm: () => {
            createTicket({
              bk_biz_id: globalBizsStore.currentBizId,
              ticket_type: 'HDFS_SHRINK',
              remark: formData.remark,
              details: {
                cluster_id: props.clusterId,
                nodes: {
                  datanode: formData.selectNodeList.map(item => ({
                    ip: item.ip,
                    bk_cloud_id: item.bk_cloud_id,
                    bk_host_id: item.bk_host_id,
                  })),
                },
              },
            }).then((data) => {
              ticketMessage(data.id);
              resolve('success');
              emits('change');
            })
              .catch(() => {
                reject();
              });
          },
        });
      });
    },
    cancel() {
      return Promise.resolve();
    },
  });
</script>
<style lang="less">
  .hdfs-cluster-shrink-box {
    padding: 18px 43px 18px 37px;
    font-size: 12px;
    line-height: 20px;
    color: #63656e;

    .item {
      & ~ .item {
        margin-top: 24px;
      }

      .item-label {
        margin-bottom: 6px;
      }
    }
  }
</style>
