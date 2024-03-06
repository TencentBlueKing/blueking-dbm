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
  <div class="capacity-form">
    <div class="spec-box mb-24">
      <div class="spec-box-item">
        <div class="spec-box-item-label">
          {{ t('当前规格') }} :
        </div>
        <div>{{ data.specName || '--' }}</div>
      </div>
      <div class="spec-box-item">
        <div class="spec-box-item-label">
          {{ t('变更后规格') }} :
        </div>
        <div>{{ currentSpec?.spec_name ? `${currentSpec?.spec_name}` : t('请先选择部署方案') }}</div>
      </div>
    </div>
    <DbForm
      form-type="vertical"
      :model="specInfo">
      <MongoConfigSpec
        v-model="specInfo"
        :biz-id="data.bizId"
        :cloud-id="data.cloudId"
        :is-apply="false"
        :origin-spec-id="originSpecId"
        :properties="{
          capacity: 'capacity',
          specId: 'spec_id'
        }"
        :shard-node-count="data.shardNodeCount"
        :shard-num="data.shardNum"
        @current-change="handleMongoConfigSpecChange" />
    </DbForm>
  </div>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import ClusterSpecModel from '@services/model/resource-spec/cluster-sepc';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { TicketTypes } from '@common/const';

  import MongoConfigSpec from '@views/mongodb-manage/components/MongoConfigSpec.vue';

  interface Props {
    data: {
      id: number,
      clusterName: string,
      specId: number,
      specName: string
      bizId: number,
      cloudId: number,
      shardNum: number;
      shardNodeCount: number;
    },
  }

  const props = defineProps<Props>();
  const isChange = defineModel<boolean>('isChange', { required: true });

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const currentSpec = ref<ClusterSpecModel & {
    shard_node_num: number;
    shard_num: number;
    shard_node_spec: string;
    machine_num: number;
    count: number;
  } | null>(null);
  const specInfo = reactive({
    capacity: 0,
    spec_id: props.data.specId,
  });

  const originSpecId = computed(() => props.data.specId);

  watch(() => specInfo.spec_id, (newSpecId) => {
    isChange.value = newSpecId > 0;
  });

  const handleMongoConfigSpecChange = (value: typeof currentSpec.value) => {
    currentSpec.value = value;
  };

  defineExpose({
    submit() {
      const currentSpecData = currentSpec.value;
      return new Promise((resolve, reject) => {
        InfoBox({
          title: t('确认变更集群容量'),
          subTitle: <p class="pb-8">{ props.data.clusterName }</p>,
          confirmText: t('确认'),
          cancelText: t('取消'),
          headerAlign: 'center',
          contentAlign: 'center',
          footerAlign: 'center',
          onClosed: () => reject(),
          onConfirm: () => {
            createTicket({
              ticket_type: TicketTypes.MONGODB_SCALE_UPDOWN,
              bk_biz_id: props.data.bizId,
              details: {
                ip_source: 'resource_pool',
                infos: [
                  {
                    cluster_id: props.data.id,
                    shard_machine_group: currentSpecData!.machine_pair,
                    shard_node_count: 3, // 固定值
                    resource_spec: {
                      mongodb: {
                        spec_id: props.data.specId,
                        count: currentSpecData!.machine_num,
                      },
                    },

                  },
                ],
              },
            })
              .then((data) => {
                ticketMessage(data.id);
                isChange.value = false;
                resolve(true);
              })
              .catch(() => {
                reject();
              });
          },
        });
      });
    },
    cancel() {
      isChange.value = false;
    },
  });
</script>

<style lang="less" scoped>
.capacity-form {
  padding: 28px 40px 24px;

  .spec-box {
    display: flex;
    flex-wrap: wrap;
    padding: 12px 16px;
    font-size: 12px;
    background-color: #FAFBFD;

    .spec-box-item {
      display: flex;
      width: 50%;
      line-height: 22px;

      .spec-box-item-label {
        min-width: 100px;
        padding-right: 8px;
        text-align: right;
      }
    }
  }

  .tips {
    display: flex;
    align-items: center;
    font-size: 12px;
  }
}
</style>
