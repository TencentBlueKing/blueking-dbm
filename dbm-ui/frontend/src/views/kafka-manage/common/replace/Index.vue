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
      v-if="originalBrokerList.length > 0"
      class="item">
      <div class="item-label">
        <span class="item-label-node">Broker</span>
        <span>（{{ $t('需添加n台', { n: originalBrokerList.length }) }}）</span>
      </div>
      <RenderNodeHostList
        ref="brokerRef"
        :data="originalBrokerList" />
    </div>
    <div
      v-if="originalZookeeperList.length > 0"
      class="item">
      <div class="item-label">
        <span class="item-label-node">Zookeeper</span>
        <span>（{{ $t('需添加n台', { n: originalZookeeperList.length }) }}）</span>
      </div>
      <RenderNodeHostList
        ref="zookeeperRef"
        :data="originalZookeeperList" />
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

  import type KafkaNodeModel from '@services/model/kafka/kafka-node';
  import { createTicket } from '@services/ticket';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { messageError } from '@utils';

  import ListNode from '../common/ListNode.vue';

  import RenderNodeHostList from './components/RenderNodeHostList.vue';

  interface Props {
    clusterId: number,
    nodeList: Array<KafkaNodeModel>
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
  const brokerRef = ref();
  const originalBrokerList = shallowRef<Array<KafkaNodeModel>>([]);
  const zookeeperRef = ref();
  const originalZookeeperList = shallowRef<Array<KafkaNodeModel>>([]);
  const remark = ref('');

  watch(() => props.nodeList, () => {
    const brokerList: Array<KafkaNodeModel> = [];
    const zookeeperList: Array<KafkaNodeModel> = [];
    props.nodeList.forEach((nodeItem) => {
      if (nodeItem.isBroker) {
        brokerList.push(nodeItem);
      } else if (nodeItem.isZookeeper) {
        zookeeperList.push(nodeItem);
      }
    });
    originalBrokerList.value = brokerList;
    originalZookeeperList.value = zookeeperList;
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    submit() {
      return new Promise((resolve, reject) => {
        const broker = brokerRef.value ? brokerRef.value.getValue() : [];
        const zookeeper = zookeeperRef.value ? zookeeperRef.value.getValue() : [];
        if (broker.length < 1 && zookeeper.length < 1) {
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
              ticket_type: 'KAFKA_REPLACE',
              bk_biz_id: currentBizId,
              remark: remark.value,
              details: {
                cluster_id: props.clusterId,
                ip_source: 'manual_input',
                old_nodes: {
                  broker: broker.map((item: any) => ({
                    bk_host_id: item.old_bk_host_id,
                    ip: item.old_ip,
                    bk_cloud_id: item.old_bk_cloud_id,
                  })),
                  zookeeper: zookeeper.map((item: any) => ({
                    bk_host_id: item.old_bk_host_id,
                    ip: item.old_ip,
                    bk_cloud_id: item.old_bk_cloud_id,
                  })),
                },
                new_nodes: {
                  broker: broker.map((item: any) => ({
                    bk_host_id: item.bk_host_id,
                    ip: item.ip,
                    bk_cloud_id: item.bk_cloud_id,
                  })),
                  zookeeper: zookeeper.map((item: any) => ({
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
