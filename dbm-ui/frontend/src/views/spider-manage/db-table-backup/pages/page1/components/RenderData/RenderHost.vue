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
    class="render-host-box"
    :class="{
      'is-repeat': isRepeat
    }">
    <TableEditInput
      ref="inputRef"
      v-model="localValue"
      :placeholder="t('请输入2台IP_英文逗号或换行分隔')"
      :rules="rules"
      textarea />
    <div
      v-if="isRepeat"
      class="repeat-flag">
      {{ t('重复') }}
    </div>
    <div
      v-if="isConflict"
      ref="handlerRef"
      class="conflict-flag">
      {{ t('冲突') }}
    </div>
    <div style="display: none;">
      <div
        ref="popRef"
        class="master-slave-clone-conflict-host-popover">
        <div class="popover-header">
          {{ t('管控区域主机冲突_请确认选择') }}
        </div>
        <div class="popover-content">
          <div
            v-for="(sameIpHostList, ipKey) in conflicHostMap"
            :key="ipKey"
            class="popover-host-item">
            <div
              v-for="item in sameIpHostList"
              :key="item.bk_cloud_id">
              <BkCheckbox
                :lbale="`${item.ip}_${item.bk_cloud_id}`"
                @change="(value: boolean) => handleConflictHostChange(item, value)">
                <span>{{ item.ip }}</span>
                <span>({{ item.bk_cloud_id }})</span>
              </BkCheckbox>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script lang="ts">
  const singleHostSelectMemo: { [key: string]: Record<string, boolean> } = {};


</script>
<script setup lang="ts">
  import _ from 'lodash';
  import tippy, {
    type Instance,
    type SingleTarget,
  } from 'tippy.js';
  import {
    computed,
    onBeforeUnmount,
    ref,
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getHostTopoInfos } from '@services/ip';
  import type { HostTopoInfo } from '@services/types/ip';

  import { useGlobalBizs } from '@stores';

  import { ipv4 } from '@common/regex';

  import TableEditInput from '@views/spider-manage/common/edit/Input.vue';

  import { random } from '@utils';

  interface Props {
    modelValue: string
  }

  interface Exposes {
    getValue: () => Promise<Array<string>>
  }

  const props = defineProps<Props>();


  const genHostKey = (hostData: HostTopoInfo) => `#${hostData.bk_cloud_id}#${hostData.ip}`;

  const instanceKey = `render_host_instance_key_${random()}`;
  singleHostSelectMemo[instanceKey] = {};

  const splitReg = /[\n,，;；]/;
  let tippyIns: Instance | undefined;

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const inputRef = ref();
  const handlerRef = ref();
  const popRef = ref();
  const localValue = ref(props.modelValue);
  const isConflict = ref(false);
  const conflicHostMap = shallowRef<Record<string, Array<HostTopoInfo>>>({});
  const conflicHostSelectMap = shallowRef<Record<string, HostTopoInfo>>({});
  // const selectRelateClusterList = shallowRef({});

  let masterHost  = {} as HostTopoInfo;
  let slaveHost = {} as HostTopoInfo;

  const rules = [
    {
      validator: (value: string) => value.split(splitReg).length >= 2,
      message: t('请输入2台IP'),
    },
    {
      validator: (value: string) => {
        const ipList = _.filter(value.split(splitReg), item => item) as Array<string>;
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
          },
          bk_biz_id: currentBizId,
        }).then((data) => {
          // eslint-disable-next-line no-param-reassign
          // data.hosts_topo_info = [
          //   ...data.hosts_topo_info,
          //   ...data.hosts_topo_info.map(item => ({
          //     ...item,
          //     bk_cloud_id: 1,
          //   })),
          // ];
          // 一个 IP 存在于多个管控区域
          if (data.hosts_topo_info.length > 2) {
            isConflict.value = true;
            conflicHostMap.value = data.hosts_topo_info.reduce((result, item) => {
              if (!result[item.ip]) {
                // eslint-disable-next-line no-param-reassign
                result[item.ip] = [];
              }
              result[item.ip].push(item);
              return result;
            }, {} as Record<string, Array<HostTopoInfo>>);
            return false;
          }
          // IP 有效
          if (data.hosts_topo_info.length === 2) {
            singleHostSelectMemo[instanceKey] = {};
            data.hosts_topo_info.forEach(((item) => {
              if (item.ip === masterIp) {
                masterHost = item;
                singleHostSelectMemo[instanceKey][genHostKey(masterHost)] = true;
              } else if (item.ip === slaveIp) {
                slaveHost = item;
                singleHostSelectMemo[instanceKey][genHostKey(slaveHost)] = true;
              }
            }));
            return true;
          }
          return false;
        });
      },
      message: t('IP不存在'),
    },
    {
      validator: () => {
        const otherHostSelectMemo = { ...singleHostSelectMemo };
        delete otherHostSelectMemo[instanceKey];
        const otherAllSelectHostMap = Object.values(otherHostSelectMemo).reduce((result, selectItem) => ({
          ...result,
          ...selectItem,
        }), {} as Record<string, boolean>);
        if (otherAllSelectHostMap[genHostKey(masterHost)] || otherAllSelectHostMap[genHostKey(slaveHost)]) {
          return false;
        }

        return true;
      },
      message: t('IP重复'),
    },
  ];

  const isRepeat = computed(() => {
    if (!localValue.value) {
      return false;
    }
    const [fisrt, last] = localValue.value.split(splitReg);
    return _.trim(fisrt) === _.trim(last);
  });

  watch(isConflict, () => {
    nextTick(() => {
      if (isConflict.value) {
        if (!handlerRef.value || tippyIns) {
          return;
        }
        tippyIns = tippy(handlerRef.value as SingleTarget, {
          content: popRef.value,
          placement: 'top',
          appendTo: () => document.body,
          theme: 'light',
          maxWidth: 'none',
          trigger: 'click',
          interactive: true,
          arrow: true,
          offset: [0, 8],
          zIndex: 999999,
          onHide() {
          // selectRelateClusterList.value = Object.values(realateCheckedMap.value);
          },
        });
      }
    });
  });

  const handleConflictHostChange = (hostData: HostTopoInfo, checked: boolean) => {
    const checkedMap = { ...conflicHostSelectMap.value };
    if (checked) {
      checkedMap[genHostKey(hostData)] = hostData;
    } else {
      delete checkedMap[genHostKey(hostData)];
    }
    conflicHostSelectMap.value = checkedMap;
  };

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  });

  defineExpose<Exposes>({
    getValue() {
      const formatHost = (item: HostTopoInfo) => ({
        ip: item.ip,
        bk_cloud_id: item.bk_cloud_id,
        bk_host_id: item.bk_host_id,
      });
      return inputRef.value
        .getValue()
        .then(() => Promise.resolve({
          new_master: formatHost(masterHost),
          new_slave: formatHost(slaveHost),
        }));
    },
  });
</script>
<style lang="less">
  .render-host-box {
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
