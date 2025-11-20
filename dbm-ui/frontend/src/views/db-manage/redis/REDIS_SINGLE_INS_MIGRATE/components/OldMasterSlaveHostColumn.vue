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
  <EditableColumn
    field="instance_data"
    :label="t('关联的主从实例')"
    :loading="loading"
    :min-width="300"
    readonly>
    <EditableBlock
      class="old-master-slave-host"
      :placeholder="t('选择集群后自动生成')">
      <div
        v-for="(item, index) in instanceInfo"
        :key="index"
        class="host-item">
        <div class="domain-item">{{ item.domain }}</div>
        <div class="instance-item">--{{ item.master.ip }}:{{ item.master.port }}</div>
        <div class="instance-item">--{{ item.slave.ip }}:{{ item.slave.port }}</div>
      </div>
    </EditableBlock>
  </EditableColumn>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getRedisInstances } from '@services/source/redis';
  import { queryMachineInstancePair } from '@services/source/redisToolbox';

  interface IHostData {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
    port: number;
  }

  interface Props {
    data: ({ instance: string } & IHostData)[];
  }

  const props = defineProps<Props>();
  const modleValue = defineModel<{
    origin_old_nodes: {
      master: IHostData[];
      slave: IHostData[];
    };
    src_cluster: {
      cluster_id: number;
      master_ins: string;
      slave_ins: string;
    }[];
  }>();

  const { t } = useI18n();

  const instanceInfo = shallowRef<
    {
      domain: string;
      master: IHostData;
      slave: IHostData;
    }[]
  >([]);

  const loading = computed(() => queryMachineInstancePairLoading.value || getRedisInstancesLoading.value);

  const { loading: queryMachineInstancePairLoading, run: runQueryMachineInstancePair } = useRequest(
    queryMachineInstancePair,
    {
      manual: true,
      onSuccess(instanceMap) {
        if (instanceMap && instanceMap.instances) {
          const masterMap = props.data!.reduce<Record<string, IHostData>>((prevMap, instanceItem) => {
            if (prevMap[instanceItem.instance]) {
              return prevMap;
            }
            return Object.assign({}, prevMap, {
              [instanceItem.instance]: {
                bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
                bk_cloud_id: instanceItem.bk_cloud_id,
                bk_host_id: instanceItem.bk_host_id,
                ip: instanceItem.ip,
                port: instanceItem.port,
              },
            });
          }, {});
          instanceInfo.value = Object.entries(masterMap).map(([masterInstance, masterInfo]) => {
            const slaveItem = instanceMap.instances![masterInstance];
            return {
              domain: slaveItem.related_clusters[0].immute_domain,
              master: masterInfo,
              slave: {
                bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
                bk_cloud_id: slaveItem.bk_cloud_id,
                bk_host_id: slaveItem.bk_host_id,
                ip: slaveItem.ip,
                port: slaveItem.port,
              },
            };
          });
        }
      },
    },
  );

  const {
    data: redisInstanceList,
    loading: getRedisInstancesLoading,
    run: runGetRedisInstances,
  } = useRequest(getRedisInstances, {
    manual: true,
  });

  watch(
    () => props.data,
    (newData, oldData) => {
      if (_.isEqual(newData, oldData)) {
        return;
      }
      if (props.data.length > 0) {
        const instances = props.data.map((item) => item.instance);
        runQueryMachineInstancePair({
          instances,
        });
        runGetRedisInstances({
          instance_address: instances.join(','),
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch([instanceInfo, redisInstanceList], () => {
    if (instanceInfo.value.length && redisInstanceList.value && redisInstanceList.value.results.length) {
      const clusterMap = redisInstanceList.value.results.reduce<Record<string, number>>(
        (prevMap, instanceItem) =>
          Object.assign({}, prevMap, { [instanceItem.instance_address]: instanceItem.cluster_id }),
        {},
      );

      const clusters: {
        cluster_id: number;
        master_ins: string;
        slave_ins: string;
      }[] = [];
      const masters: IHostData[] = [];
      const slaves: IHostData[] = [];

      instanceInfo.value.forEach((item) => {
        const clusterId = clusterMap[`${item.master.ip}:${item.master.port}`];
        clusters.push({
          cluster_id: clusterId,
          master_ins: `${item.master.ip}:${item.master.port}`,
          slave_ins: `${item.slave.ip}:${item.slave.port}`,
        });
        masters.push(item.master);
        slaves.push(item.slave);
      });

      modleValue.value = {
        origin_old_nodes: {
          master: masters,
          slave: slaves,
        },
        src_cluster: clusters,
      };
    }
  });
</script>

<style lang="less" scoped>
  .old-master-slave-host {
    .domain-item {
      color: #4d4f56;
    }

    .instance-item {
      color: #979ba5;
    }
  }
</style>
