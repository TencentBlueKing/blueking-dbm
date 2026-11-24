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
  <div class="render-cluster-role">
    <template v-if="renderList.length < 1"> -- </template>
    <template v-else>
      <DbTag
        v-for="item in renderList"
        :key="item"
        class="mr-4">
        {{ item }}
      </DbTag>
    </template>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    data: Array<string>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  // 实例角色 -> 展示文案，与各集群列表 RoleColumn 的 label 保持一致
  const roleLabelMap: Record<string, string> = {
    // mysql / sqlserver
    backend_master: 'Master',
    backend_slave: 'Slave',
    // kafka
    broker: 'Broker',
    // doris
    doris_backend_cold: t('冷节点'),
    doris_backend_hot: t('热节点'),
    doris_backend_warm: t('温节点'),
    doris_follower: t('Follower节点'),
    doris_observer: t('Observer节点'),
    // es
    es_client: t('Client节点'),
    es_datanode_cold: t('冷节点'),
    es_datanode_hot: t('热节点'),
    es_master: t('Master节点'),
    // hdfs
    hdfs_datanode: 'DataNode',
    hdfs_journalnode: 'Journalnode',
    hdfs_namenode: 'NameNode',
    hdfs_zookeeper: 'Zookeeper',
    orphan: t('实例'),
    // oracle
    primary: 'Primary',
    // redis / mysql proxy
    proxy: 'Proxy',
    // pulsar
    pulsar_bookkeeper: 'Bookkeeper',
    pulsar_broker: 'Broker',
    pulsar_zookeeper: 'Zookeeper',
    redis_master: 'Master',
    redis_slave: 'Slave',
    // tendbcluster
    remote_master: 'RemoteDB',
    remote_slave: 'RemoteDR',
    // riak
    riak_node: t('节点'),
    spider_master: 'Spider Master',
    spider_mnt: t('运维节点'),
    spider_slave: 'Spider Slave',
    standby: 'Standby',
    zookeeper: 'Zookeeper',
  };

  // 过滤空值；未登记的角色（如 mongodb 的 m1/backup、已是展示文案的值）原样展示
  const renderList = computed(() =>
    props.data.filter((item) => Boolean(item)).map((item) => roleLabelMap[item] || item),
  );
</script>
<style lang="less">
  .render-cluster-role {
    display: block;
  }
</style>
