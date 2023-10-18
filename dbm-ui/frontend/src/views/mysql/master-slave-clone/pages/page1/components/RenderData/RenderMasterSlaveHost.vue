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
  <div
    class="render-master-slave-box"
    :class="{
      'is-repeat': isRepeat
    }">
    <TableEditInput
      ref="inputRef"
      v-model="localIpText"
      :disabled="disabled"
      :placeholder="$t('请输入2台IP_英文逗号或换行分隔')"
      :rules="rules"
      textarea />
    <div
      v-if="isRepeat"
      class="repeat-flag">
      {{ $t('重复') }}
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import {
    computed,
    ref,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  // TODO INTERFACE done
  // import { getHostTopoInfos } from '@services/ip';
  import { getHostTopoInfos } from '@services/source/ipchooser';
  import type { HostTopoInfo } from '@services/types/ip';

  import { useGlobalBizs } from '@stores';

  import { ipv4 } from '@common/regex';

  import TableEditInput from '@views/mysql/common/edit/Input.vue';

  import { random } from '@utils';

  import type { IHostData } from './Row.vue';

  interface Props {
    masterHost?: IHostData,
    slaveHost?: IHostData,
    domain?: string,
    disabled: boolean,
    cloudId: null | number
  }

  interface Exposes {
    getValue: () => Promise<IHostData>
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

  let masterHostMemo  = {} as HostTopoInfo;
  let slaveHostMemo = {} as HostTopoInfo;
  let errorMessage = t('IP不存在');

  const rules = [
    {
      validator: (value: string) => {
        const ipList = _.filter(value.split(splitReg), item => _.trim(item)) as Array<string>;
        return ipList.length === 2;
      },
      message: t('请输入2台IP'),
    },
    {
      validator: (value: string) => {
        const ipList = value.split(splitReg) as Array<string>;
        return _.every(ipList, item => ipv4.test(_.trim(item)));
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
        const [masterIp, slaveIp] = value.split(splitReg);
        return getHostTopoInfos({
          filter_conditions: {
            bk_host_innerip: [masterIp, slaveIp],
            mode: 'idle_only',
          },
          bk_biz_id: currentBizId,
        }).then((data) => {
          if (data.hosts_topo_info.length < 2) {
            const existIps = data.hosts_topo_info.map(item => item.ip);
            const ips = [masterIp, slaveIp].filter(ip => !existIps.includes(ip));
            errorMessage = t('ips不在空闲机中', { ips: ips.join('、') });
            return false;
          }

          const qualifiedHosts = data.hosts_topo_info.filter(item => item.bk_cloud_id === props.cloudId);
          if (qualifiedHosts.length !== 2) {
            const qualifiedIps = qualifiedHosts.map(item => item.ip);
            errorMessage = t('新主机xx跟目标集群xx须在同一个管控区域', {
              ip: [masterIp, slaveIp]
                .filter(ip => !qualifiedIps.includes(ip))
                .join(', '),
              cluster: props.domain,
            });
            return false;
          }

          // IP 有效
          singleHostSelectMemo[instanceKey] = {};
          data.hosts_topo_info.forEach(((item) => {
            if (item.ip === masterIp && item.bk_cloud_id === props.cloudId) {
              masterHostMemo = item;
              singleHostSelectMemo[instanceKey][genHostKey(masterHostMemo)] = true;
            } else if (item.ip === slaveIp && item.bk_cloud_id === props.cloudId) {
              slaveHostMemo = item;
              singleHostSelectMemo[instanceKey][genHostKey(slaveHostMemo)] = true;
            }
          }));
          return true;
        });
      },
      message: () => errorMessage,
    },
    {
      validator: () => {
        const otherHostSelectMemo = { ...singleHostSelectMemo };
        delete otherHostSelectMemo[instanceKey];

        const otherAllSelectHostMap = Object.values(otherHostSelectMemo).reduce((result, selectItem) => ({
          ...result,
          ...selectItem,
        }), {} as Record<string, boolean>);
        if (otherAllSelectHostMap[genHostKey(masterHostMemo)]
          || otherAllSelectHostMap[genHostKey(slaveHostMemo)]) {
          return false;
        }

        return true;
      },
      message: t('IP重复'),
    },
  ];

  const isRepeat = computed(() => {
    if (!localIpText.value) {
      return false;
    }
    const [fisrt, last] = localIpText.value.split(splitReg);
    return _.trim(fisrt) === _.trim(last);
  });

  // 同步外部主从机器
  watch(() => [props.masterHost, props.slaveHost], () => {
    const ipStack = [];
    if (props.masterHost) {
      ipStack.push(props.masterHost.ip);
    }
    if (props.slaveHost) {
      ipStack.push(props.slaveHost.ip);
    }
    localIpText.value = ipStack.join(';');
  }, {
    immediate: true,
  });


  defineExpose<Exposes>({
    getValue() {
      const formatHost = (item: HostTopoInfo) => ({
        bk_biz_id: currentBizId,
        bk_host_id: item.bk_host_id,
        bk_cloud_id: item.bk_cloud_id,
        ip: item.ip,
      });
      return inputRef.value
        .getValue()
        .then(() => Promise.resolve({
          new_master: formatHost(masterHostMemo),
          new_slave: formatHost(slaveHostMemo),
        }));
    },
  });
</script>
<style lang="less" scoped>
  .render-master-slave-box {
    position: relative;

    &.is-repeat {
      .input-error {
        display: none;
      }
    }

    .repeat-flag,
    .conflict-flag {
      position: absolute;
      top: 50%;
      right: 0;
      display: flex;
      height: 20px;
      padding: 0 5px;
      font-size: 12px;
      line-height: 20px;
      color: #fff;
      background-color: #ea3636;
      border-radius: 2px;
      align-self: center;
      transform: scale(0.8) translateY(-50%);
    }
  }

  .master-slave-clone-conflict-host-popover {
    padding: 9px 7px;

    .popover-header {
      margin-bottom: 8px;
      font-size: 12px;
      font-weight: bold;
      line-height: 16px;
      color: #313238;
    }

    .popover-content {
      max-height: 300px;
      overflow: auto;
    }

    .popover-host-item {
      padding: 2px 20px 2px 0;

      &:nth-child(n+2) {
        border-top: 1px solid #dcdee5;
      }
    }
  }
</style>
