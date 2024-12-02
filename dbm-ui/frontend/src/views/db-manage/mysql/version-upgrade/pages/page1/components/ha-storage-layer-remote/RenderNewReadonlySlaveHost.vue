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
  <TableEditInput
    ref="inputRef"
    v-model="localIpText"
    :disabled="!slaveList?.length"
    :paste-fn="pasteFunc"
    :placeholder="placeholder"
    :rules="rules" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { getHostTopoInfos } from '@services/source/ipchooser';

  import { useGlobalBizs } from '@stores';

  import { ipv4 } from '@common/regex';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import { random } from '@utils';

  import type { IHostData } from './Row.vue';

  type HostTopoInfo = ServiceReturnType<typeof getHostTopoInfos>['hosts_topo_info'][number];

  interface Props {
    domain?: string;
    cloudId?: number;
    slaveList?: IHostData[];
    ipList?: IHostData[];
  }

  interface Exposes {
    getValue: () => Promise<{
      read_only_slaves: {
        old_slave: IHostData;
        new_slave: IHostData;
      }[];
    }>;
  }

  const props = defineProps<Props>();

  const genHostKey = (hostData: HostTopoInfo) => `#${hostData.bk_cloud_id}#${hostData.ip}`;

  const instanceKey = `master_slave_host_${random()}`;
  const singleHostSelectMemo: { [key: string]: Record<string, boolean> } = {};

  const splitReg = /[\n ,，;；]/;

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const inputRef = ref();
  const localIpText = ref('');

  let slaveHostMemo = [] as HostTopoInfo[];
  let errorMessage = t('IP不存在');

  const rules = [
    {
      validator: (value: string) => {
        const ipList = value.split(splitReg);
        return ipList.length === (props.slaveList?.length || 0);
      },
      message: t('请输入n台IP', { n: props.slaveList?.length || 0 }),
    },
    {
      validator: (value: string) => {
        const ipList = value.split(splitReg);
        return _.every(ipList, (item) => ipv4.test(_.trim(item)));
      },
      message: t('IP格式不正确'),
    },
    {
      validator: (value: string) => {
        const [fisrt, last] = value.split(splitReg);
        return _.trim(fisrt) !== _.trim(last);
      },
      message: t('输入的主从IP重复'),
    },
    {
      validator: (value: string) => {
        const ipList = value.split(splitReg);
        return getHostTopoInfos({
          filter_conditions: {
            bk_host_innerip: ipList,
            mode: 'idle_only',
          },
          bk_biz_id: currentBizId,
        }).then((data) => {
          if (data.hosts_topo_info.length < (props.slaveList?.length || 0)) {
            const existIps = data.hosts_topo_info.map((item) => item.ip);
            const ips = ipList.filter((ip) => !existIps.includes(ip));
            errorMessage = t('ips不在空闲机中', { ips: ips.join('、') });
            return false;
          }

          const qualifiedHosts = data.hosts_topo_info.filter((item) => item.bk_cloud_id === props.cloudId);
          if (qualifiedHosts.length !== (props.slaveList?.length || 0)) {
            const qualifiedIps = qualifiedHosts.map((item) => item.ip);
            errorMessage = t('新主机xx跟目标集群xx须在同一个管控区域', {
              ip: ipList.filter((ip) => !qualifiedIps.includes(ip)).join(', '),
              cluster: props.domain,
            });
            return false;
          }

          // IP 有效
          singleHostSelectMemo[instanceKey] = {};
          slaveHostMemo = [];
          // 新只读主机和旧只读主机是对应关系，需要按输入的顺序提单
          const topoHostMap = data.hosts_topo_info.reduce<Record<string, (typeof data.hosts_topo_info)[number]>>(
            (prev, item) => Object.assign({}, prev, { [item.ip]: item }),
            {},
          );
          ipList.forEach((inputIpItem) => {
            const topoHostItem = topoHostMap[inputIpItem];
            if (topoHostItem) {
              slaveHostMemo.push(topoHostItem);
              singleHostSelectMemo[instanceKey][genHostKey(topoHostItem)] = true;
            }
          });
          return true;
        });
      },
      message: () => errorMessage,
    },
  ];

  const placeholder = computed(() => {
    if (props.slaveList?.length) {
      return t('请输入n台IP_英文逗号或换行分隔', { n: props.slaveList.length || 0 });
    }
    return t('无只读主机');
  });

  watchEffect(() => {
    localIpText.value = (props.ipList || []).map((item) => item.ip).join(';');
  });

  const pasteFunc = (value: string) => value.split(splitReg).join(',');

  defineExpose<Exposes>({
    getValue() {
      const formatHost = (item: HostTopoInfo) => ({
        bk_biz_id: currentBizId,
        bk_host_id: item.bk_host_id,
        bk_cloud_id: item.bk_cloud_id,
        ip: item.ip,
      });

      if (props.slaveList?.length) {
        return inputRef.value.getValue().then(() => {
          const oldSlaveList = props.slaveList!;
          const newSlaveList = slaveHostMemo.map((slaveItem) => formatHost(slaveItem));
          const result = oldSlaveList.map((slaveItem, index) => ({
            old_slave: slaveItem,
            new_slave: newSlaveList[index],
          }));

          return Promise.resolve({
            read_only_slaves: result,
          });
        });
      }

      return Promise.resolve({
        read_only_slaves: [],
      });
    },
  });
</script>
