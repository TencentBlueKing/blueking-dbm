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
  <div class="es-cluster-replace-box">
    <div
      v-if="originalHotList.length > 0"
      class="item">
      <div class="item-label">
        <span class="item-label-node">{{ $t('热节点') }}</span>
        <span>（{{ $t('需添加n台', { n: originalHotList.length }) }}）</span>
      </div>
      <RenderNodeHostList
        ref="hotRef"
        :data="originalHotList"
        instnace-number-editable />
    </div>
    <div
      v-if="originalColdList.length > 0"
      class="item">
      <div class="item-label">
        <span class="item-label-node">{{ $t('冷节点') }}</span>
        <span>（{{ $t('需添加n台', { n: originalColdList.length }) }}）</span>
      </div>
      <RenderNodeHostList
        ref="coldRef"
        :data="originalColdList"
        instnace-number-editable />
    </div>
    <div
      v-if="originalClientList.length > 0"
      class="item">
      <div class="item-label">
        <span class="item-label-node">{{ $t('Client节点') }}</span>
        <span>（{{ $t('需添加n台', { n: originalClientList.length }) }}）</span>
      </div>
      <RenderNodeHostList
        ref="clientRef"
        :data="originalClientList" />
    </div>
    <div
      v-if="originalMasterList.length > 0"
      class="item">
      <div class="item-label">
        <span class="item-label-node">{{ $t('Master节点') }}</span>
        <span>（{{ $t('需添加n台', { n: originalMasterList.length }) }}）</span>
      </div>
      <RenderNodeHostList
        ref="masterRef"
        :data="originalMasterList" />
    </div>
    <div class="item">
      <div class="item-label">
        {{ $t('备注') }}
      </div>
      <BkInput
        v-model="remark"
        :maxlength="100"
        :placeholder="$t('请提供更多有用信息申请信息_以获得更快审批')"
        type="textarea" />
    </div>
    <ListNode
      v-model="listData"
      v-model:is-show="isShowListNode"
      :cluster-id="clusterId" />
  </div>
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import {
    ref,
    shallowRef,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type EsNodeModel from '@services/model/es/es-node';
  import { createTicket } from '@services/ticket';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { messageError } from '@utils';

  import ListNode from '../common/ListNode.vue';

  import RenderNodeHostList from './components/RenderNodeHostList.vue';

  interface Props {
    clusterId: number,
    nodeList: Array<EsNodeModel>
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

  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();
  const { t } = useI18n();

  const isShowListNode = ref(false);
  const listData = shallowRef([]);
  const hotRef = ref();
  const originalHotList = shallowRef<Array<EsNodeModel>>([]);
  const coldRef = ref();
  const originalColdList = shallowRef<Array<EsNodeModel>>([]);
  const clientRef = ref();
  const originalClientList = shallowRef<Array<EsNodeModel>>([]);
  const masterRef = ref();
  const originalMasterList = shallowRef<Array<EsNodeModel>>([]);
  const remark = ref('');

  watch(() => props.nodeList, () => {
    const hotList: Array<EsNodeModel> = [];
    const coldList: Array<EsNodeModel> = [];
    const clientList: Array<EsNodeModel> = [];
    const masterList: Array<EsNodeModel> = [];

    props.nodeList.forEach((nodeItem) => {
      if (nodeItem.isHot) {
        hotList.push(nodeItem);
      } else if (nodeItem.isCold) {
        coldList.push(nodeItem);
      } else if (nodeItem.isClient) {
        clientList.push(nodeItem);
      } else if (nodeItem.isMaster) {
        masterList.push(nodeItem);
      }
    });
    originalHotList.value = hotList;
    originalColdList.value = coldList;
    originalClientList.value = clientList;
    originalMasterList.value = masterList;
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    submit() {
      return new Promise((resolve, reject) => {
        const hot = hotRef.value ? hotRef.value.getValue() : [];
        const cold = coldRef.value ? coldRef.value.getValue() : [];
        const client = clientRef.value ? clientRef.value.getValue() : [];
        const master = masterRef.value ? masterRef.value.getValue() : [];

        if (hot.length < 1
          && cold.length < 1
          && client.length < 1
          && master.length < 1) {
          messageError(t('替换节点不能为空'));
          return reject();
        }
        InfoBox({
          title: t('确认替换集群'),
          subTitle: '',
          confirmText: t('确认'),
          cancelText: t('取消'),
          headerAlign: 'center',
          contentAlign: 'center',
          footerAlign: 'center',
          onClosed: () => reject(),
          onConfirm: () => {
            createTicket({
              ticket_type: 'ES_REPLACE',
              bk_biz_id: currentBizId,
              remark: remark.value,
              details: {
                cluster_id: props.clusterId,
                ip_source: 'manual_input',
                old_nodes: {
                  hot: hot.map((item: any) => ({
                    bk_host_id: item.old_bk_host_id,
                    ip: item.old_ip,
                    instance_num: item.old_instance_num,
                    bk_cloud_id: item.old_bk_cloud_id,
                  })),
                  cold: cold.map((item: any) => ({
                    bk_host_id: item.old_bk_host_id,
                    ip: item.old_ip,
                    instance_num: item.old_instance_num,
                    bk_cloud_id: item.old_bk_cloud_id,
                  })),
                  client: client.map((item: any) => ({
                    bk_host_id: item.old_bk_host_id,
                    ip: item.old_ip,
                    bk_cloud_id: item.old_bk_cloud_id,
                  })),
                  master: master.map((item: any) => ({
                    bk_host_id: item.old_bk_host_id,
                    ip: item.old_ip,
                    bk_cloud_id: item.old_bk_cloud_id,
                  })),
                },
                new_nodes: {
                  hot: hot.map((item: any) => ({
                    bk_host_id: item.bk_host_id,
                    ip: item.ip,
                    instance_num: item.instance_num,
                    bk_cloud_id: item.bk_cloud_id,
                  })),
                  cold: cold.map((item: any) => ({
                    bk_host_id: item.bk_host_id,
                    ip: item.ip,
                    instance_num: item.instance_num,
                    bk_cloud_id: item.bk_cloud_id,
                  })),
                  client: client.map((item: any) => ({
                    bk_host_id: item.bk_host_id,
                    ip: item.ip,
                    bk_cloud_id: item.bk_cloud_id,
                  })),
                  master: master.map((item: any) => ({
                    bk_host_id: item.bk_host_id,
                    ip: item.ip,
                    bk_cloud_id: item.bk_cloud_id,
                  })),
                },
              },
            })
              .then((data) => {
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
  .es-cluster-replace-box {
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

        .item-label-node {
          font-weight: bold;
          color: #313238;
        }
      }
    }
  }
</style>
