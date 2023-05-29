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
  <BkDialog
    :is-show="isShow"
    :title="$t('添加从库_批量录入')"
    :width="705"
    @closed="handleClosed">
    <div class="master-slave-swap-batch-entry">
      <div class="header">
        <table>
          <thead>
            <tr>
              <th>{{ $t('主库主机') }} </th>
              <th>{{ $t('从库主机') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>127.0.0.2</td>
              <td>
                <span>127.0.0.1</span>
                <span
                  v-bk-tooltips="$t('复制')"
                  class="copy-btn"
                  @click="handleCopy">
                  <DbIcon type="copy" />
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div ref="inputRef">
        <BkInput
          v-model="localValue"
          :placeholder="placeholder"
          style="height: 320px; margin: 12px 0 30px;"
          type="textarea"
          @input="handleInputChange" />
      </div>
      <div class="error-box">
        <span v-if="inputInvalidStack.length > 0">
          <span>{{ $t('n处格式错误', [inputInvalidStack.length]) }}</span>
          <DbIcon
            class="action-btn"
            type="audit"
            @click="handleHighInvalid" />
        </span>
        <span v-if="inputErrorStack.length > 0">
          <span v-if="inputInvalidStack.length > 0">；</span>
          <span>{{ $t('n处缺少匹配对象', [inputErrorStack.length]) }}</span>
          <DbIcon
            class="action-btn"
            type="audit"
            @click="handleHighError" />
        </span>
        <span v-if="inputHostErrorStack.length > 0">
          <span v-if="inputInvalidStack.length > 0">；</span>
          <span>{{ $t('n处主机IP不存在', [inputHostErrorStack.length]) }}</span>
          <DbIcon
            class="action-btn"
            type="audit"
            @click="handleHighClusterError" />
        </span>
      </div>
    </div>
    <template #footer>
      <BkButton
        :loading="isChecking"
        theme="primary"
        @click="handleSubmit">
        {{ $t('确定') }}
      </BkButton>
      <BkButton
        class="ml8"
        @click="handleClosed">
        {{ $t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script lang="ts">
  export interface IValue {
    masterData: {
      bk_host_id: number,
      bk_cloud_id: number,
      ip: string,
    },
    slaveData: {
      bk_cloud_id: number,
      bk_host_id: number,
      ip: string,
    },
  }
</script>
<script setup lang="ts">
  import _ from 'lodash';
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getHostTopoInfos } from '@services/ip';
  import type { HostTopoInfo } from '@services/types/ip';

  import { useGlobalBizs } from '@stores';

  import { ipv4 } from '@common/regex';

  import { execCopy } from '@/utils';


  interface IInputParse {
    masterIp: string,
    slaveIp: string,
  }

  interface Props {
    isShow: boolean;
  }
  interface Emits {
    (e: 'update:isShow', value: boolean): void;
    (e: 'change', value: Array<IValue>): void;
  }

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const getInputTextList = (list: Array<IInputParse>) => list.map(item => `${item.masterIp} ${item.slaveIp}`);

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const placeholder = t('请分别输入主库主机_从库主机_多个对象_换行分隔');

  const inputRef = ref();
  const isChecking = ref(false);
  const localValue = ref('');

  const inputInvalidStack = ref<Array<IInputParse>>([]);
  const inputErrorStack = ref<Array<IInputParse>>([]);
  const inputHostErrorStack = ref<Array<IInputParse>>([]);

  const handleCopy = () => {
    execCopy('127.0.0.2    127.0.0.1\n');
  };

  const handleClosed = () => {
    emits('update:isShow', false);
  };


  const handleSubmit = () => {
    const inputRecordList =  localValue.value.split('\n');

    const validList: Array<IInputParse> = [];
    const invalidList: Array<IInputParse> = [];
    const errorList: Array<IInputParse> = [];

    inputRecordList.forEach((recordItem) => {
      if (!_.trim(recordItem)) {
        return;
      }
      const ipList = recordItem.split(/ +/).filter(item => _.trim(item));
      if (ipList.length !== 2) {
        errorList.push({
          masterIp: recordItem,
          slaveIp: '',
        });
        return;
      }
      const [masterIp, slaveIp] = ipList;
      const payload = {
        masterIp,
        slaveIp,
      };

      if (!ipv4.test(masterIp) || !ipv4.test(slaveIp)) {
        invalidList.push(payload);
        return;
      }

      validList.push(payload);
    });

    isChecking.value = true;
    const allValidIpList = validList.reduce((result, item) => [
      ...result,
      item.masterIp,
      item.slaveIp,
    ], [] as string[]);
    getHostTopoInfos({
      filter_conditions: {
        bk_host_innerip: allValidIpList,
      },
      bk_biz_id: currentBizId,
    }).then((data) => {
      const realDataMap = data.hosts_topo_info.reduce((result, item) => ({
        ...result,
        [item.ip]: item,
      }), {} as Record<string, HostTopoInfo>);

      const resultList: Array<IValue> = [];
      const hostErrorList: Array<IInputParse> = [];

      validList.forEach((inputData) => {
        if (!realDataMap[inputData.masterIp] || !realDataMap[inputData.slaveIp]) {
          hostErrorList.push(inputData);
        } else {
          const getValue = ({
            bk_host_id,
            bk_cloud_id,
            ip,
          }: HostTopoInfo) => ({
            bk_host_id,
            bk_cloud_id,
            ip,
          });
          resultList.push({
            masterData: getValue(realDataMap[inputData.masterIp]),
            slaveData: getValue(realDataMap[inputData.slaveIp]),
          });
        }
      });
      inputInvalidStack.value = invalidList;
      inputErrorStack.value = errorList;
      inputHostErrorStack.value = hostErrorList;
      if (invalidList.length < 1
        && errorList.length < 1
        && hostErrorList.length < 1) {
        emits('change', resultList);
        handleClosed();
      } else {
        localValue.value = _.filter([
          ...invalidList.map(item => getInputTextList([item])),
          ...errorList.map(item => getInputTextList([item])),
          ...hostErrorList.map(item => getInputTextList([item])),
          ...resultList.map(item => `${item.masterData.ip} ${item.slaveData.ip}`),
        ]).join('\n');
      }
    })
      .finally(() => {
        isChecking.value = false;
      });
  };

  const handleInputChange = () => {
    inputInvalidStack.value = [];
    inputErrorStack.value = [];
    inputHostErrorStack.value = [];
  };

  const handleHighInvalid = () => {
    const $inputEl = inputRef.value.querySelector('textarea');
    const invalidText = getInputTextList(inputInvalidStack.value).join('\n');
    $inputEl.focus();
    $inputEl.selectionStart = 0;
    $inputEl.selectionEnd = invalidText.length;
  };

  const handleHighError = () => {
    const $inputEl = inputRef.value.querySelector('textarea');
    $inputEl.focus();
    const invalidText = getInputTextList(inputInvalidStack.value).join('\n');
    const errorText = getInputTextList(inputErrorStack.value).join('\n');

    const startIndex = invalidText.length > 0 ? invalidText.length + 1 : 0;
    $inputEl.selectionStart = startIndex;
    $inputEl.selectionEnd = startIndex + errorText.length;
  };

  const handleHighClusterError = () => {
    const $inputEl = inputRef.value.querySelector('textarea');
    $inputEl.focus();
    const invalidText = [
      ...getInputTextList(inputInvalidStack.value),
      ...getInputTextList(inputErrorStack.value),
    ].join('\n');
    const clusterErrorText = getInputTextList(inputHostErrorStack.value).join('\n');

    const startIndex = invalidText.length > 0 ? invalidText.length + 1 : 0;
    $inputEl.selectionStart = startIndex;
    $inputEl.selectionEnd = startIndex + clusterErrorText.length;
  };
</script>
<style lang="less">
  .master-slave-swap-batch-entry {
    .header {
      width: 100%;
      padding: 6px 0;
      font-size: 12px;
      color: #63656e;
      text-align: left;
      background: #f5f7fa;
      border-radius: 2px;

      th,
      td {
        padding: 5px 16px;
        line-height: 16px;
      }

      .copy-btn {
        margin-left: 18px;
        color: #3a84ff;
        cursor: pointer;
      }
    }

    .error-box {
      position: absolute;
      margin-top: -25px;
      font-size: 12px;
      font-weight: bold;
      color: #ea3636;

      .action-btn {
        padding: 0 4px;
        color: #979ba5;
        cursor: pointer;
      }
    }

    textarea {
      &::selection {
        color: #63656e;
        background: #fdd;
      }
    }
  }
</style>
