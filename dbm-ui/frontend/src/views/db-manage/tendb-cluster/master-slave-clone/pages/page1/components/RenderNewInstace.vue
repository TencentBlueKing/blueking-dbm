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
      'is-repeat': isRepeat,
    }"
    @mouseenter="handleControlShowEdit(true)"
    @mouseleave="handleControlShowEdit(false)">
    <TableEditInput
      ref="inputRef"
      v-model="localValue"
      :disabled="!clusterData.ip"
      :placeholder="t('请输入2台IP_英文逗号或换行分隔')"
      :rules="rules"
      textarea
      @input-error="handleInputError" />
    <div
      v-if="showEditIcon"
      v-bk-tooltips="{
        disabled: !!clusterData.ip,
        content: t('请先选择目标主库主机'),
      }"
      class="host-select"
      :style="{ right: errorMessage ? '30px' : '' }">
      <BkButton
        class="host-select-btn"
        :disabled="!clusterData.ip"
        @click="handleShowIpSelector">
        <DbIcon
          class="select-icon"
          type="host-select" />
      </BkButton>
    </div>
    <BkTag
      v-if="isRepeat"
      class="repeat-flag"
      size="small"
      theme="warning">
      {{ t('重复') }}
    </BkTag>
    <BkTag
      v-if="isConflict"
      ref="handlerRef"
      class="conflict-flag"
      size="small"
      theme="warning">
      {{ t('冲突') }}
    </BkTag>
    <div style="display: none">
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
    <IpSelector
      v-if="clusterData"
      v-model:show-dialog="isShowIpSelector"
      :biz-id="currentBizId"
      button-text=""
      :cloud-info="{
        id: clusterData.cloudId,
        name: clusterData.cloudName,
      }"
      :data="localHostList"
      :disable-dialog-submit-method="disableDialogSubmitMethod"
      :disable-host-method="disableHostMethod"
      :os-types="[OSTypes.Linux]"
      service-mode="idle_only"
      :show-view="false"
      @change="handleHostChange">
      <template #submitTips="{ hostList: resultHostList }">
        <I18nT
          keypath="需n台_已选n台"
          style="font-size: 14px; color: #63656e"
          tag="span">
          <span
            class="number"
            style="color: #2dcb56">
            2
          </span>
          <span
            class="number"
            style="color: #3a84ff">
            {{ resultHostList.length }}
          </span>
        </I18nT>
      </template>
    </IpSelector>
  </div>
</template>

<script lang="ts">
  const singleHostSelectMemo: { [key: string]: Record<string, boolean> } = {};
</script>

<script setup lang="ts">
  import _ from 'lodash';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import { checkHost, getHostTopoInfos } from '@services/source/ipchooser';
  import type { HostInfo } from '@services/types/ip';

  import { useGlobalBizs } from '@stores';

  import { OSTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import TableEditInput from '@views/db-manage/tendb-cluster/common/edit/Input.vue';

  import { random } from '@utils';

  import type { IDataRow } from './Row.vue';

  type HostTopoInfo = ServiceReturnType<typeof getHostTopoInfos>['hosts_topo_info'][number];

  interface Props {
    clusterData: IDataRow['clusterData'];
    newHostList: IDataRow['newHostList'];
  }

  interface Exposes {
    getValue: () => Promise<
      {
        ip: string;
        bk_cloud_id: number;
        bk_host_id: number;
        bk_biz_id: number;
      }[]
    >;
  }

  const props = defineProps<Props>();

  const genHostKey = (hostData: HostTopoInfo) => `#${hostData.bk_cloud_id}#${hostData.ip}`;

  const instanceKey = `render_host_instance_key_${random()}`;
  singleHostSelectMemo[instanceKey] = {};

  const splitReg = /[\n,]/;
  let tippyIns: Instance | undefined;

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const inputRef = ref();
  const handlerRef = ref();
  const popRef = ref();
  const localValue = ref();
  const isConflict = ref(false);
  const isShowIpSelector = ref(false);
  const errorMessage = ref('');
  const showEditIcon = ref(false);

  const conflicHostMap = shallowRef<Record<string, Array<HostTopoInfo>>>({});
  const conflicHostSelectMap = shallowRef<Record<string, HostTopoInfo>>({});
  const localHostList = shallowRef<HostInfo[]>([]);

  let masterHost = {} as HostTopoInfo;
  let slaveHost = {} as HostTopoInfo;

  const rules = [
    {
      validator: (value: string) => value.split(splitReg).length === 2,
      message: t('请输入2台IP'),
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
        const [masterIp, slaveIp] = value.split(splitReg);
        return getHostTopoInfos({
          filter_conditions: {
            bk_host_innerip: [masterIp, slaveIp],
          },
          bk_biz_id: currentBizId,
        }).then(async (data) => {
          // 一个 IP 存在于多个管控区域
          if (data.hosts_topo_info.length > 2) {
            isConflict.value = true;
            conflicHostMap.value = data.hosts_topo_info.reduce(
              (result, item) => {
                if (!result[item.ip]) {
                  Object.assign(result, {
                    [item.ip]: [],
                  });
                }
                result[item.ip].push(item);
                return result;
              },
              {} as Record<string, Array<HostTopoInfo>>,
            );
            return false;
          }
          // IP 有效
          if (data.hosts_topo_info.length === 2) {
            singleHostSelectMemo[instanceKey] = {};
            data.hosts_topo_info.forEach((item) => {
              if (item.ip === masterIp) {
                masterHost = item;
                singleHostSelectMemo[instanceKey][genHostKey(masterHost)] = true;
              } else if (item.ip === slaveIp) {
                slaveHost = item;
                singleHostSelectMemo[instanceKey][genHostKey(slaveHost)] = true;
              }
            });
            if (!_.isEmpty(masterHost) && !_.isEmpty(slaveHost)) {
              const hostList = await checkHost({
                ip_list: [masterHost.ip, slaveHost.ip],
                scope_list: [
                  {
                    scope_id: currentBizId,
                    scope_type: 'biz',
                  },
                ],
                mode: 'all',
              });
              localHostList.value = hostList;
            }
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
        const otherAllSelectHostMap = Object.values(otherHostSelectMemo).reduce(
          (result, selectItem) => ({
            ...result,
            ...selectItem,
          }),
          {} as Record<string, boolean>,
        );
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

  watch(
    () => props.newHostList,
    () => {
      localValue.value = props.newHostList.join(',');
    },
    {
      immediate: true,
    },
  );

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
        });
      }
    });
  });

  const handleControlShowEdit = (isShow: boolean) => {
    showEditIcon.value = isShow;
  };

  const handleInputError = (value: string) => {
    errorMessage.value = value;
  };

  const handleShowIpSelector = () => {
    isShowIpSelector.value = true;
  };

  const disableDialogSubmitMethod = (hostList: HostInfo[]) => (hostList.length === 2 ? false : t('需n台', { n: 2 }));

  const disableHostMethod = (data: HostInfo, list: HostInfo[]) => (list.length >= 2 ? t('仅需n台', { n: 2 }) : false);

  const handleHostChange = (hostList: HostInfo[]) => {
    localHostList.value = hostList;
    localValue.value = hostList.map((hostItem) => hostItem.ip).join(',');
  };

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
    singleHostSelectMemo[instanceKey] = {};
  });

  defineExpose<Exposes>({
    getValue() {
      const hostList = localHostList.value.map((hostItem) => ({
        ip: hostItem.ip,
        bk_cloud_id: hostItem.cloud_id,
        bk_host_id: hostItem.host_id,
        bk_biz_id: hostItem.biz.id,
      }));
      return inputRef
        .value!.getValue()
        .then(() => Promise.resolve(hostList))
        .catch(() => Promise.reject(hostList));
    },
  });
</script>
<style lang="less">
  .render-host-box {
    position: relative;

    .host-select {
      position: absolute;
      top: 0;
      right: 5px;
      z-index: 999;
    }

    .host-select-btn {
      width: 24px;
      height: 24px;
      padding: 0;
      background-color: #f0f1f5;
      border: none;
    }

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
      height: 20px;
      padding: 0 5px;
      line-height: 20px;
      transform: translateY(-50%);
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

      &:nth-child(n + 2) {
        border-top: 1px solid #dcdee5;
      }
    }
  }
</style>
