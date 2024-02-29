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
    :width="1200"
    @closed="handleClosed">
    <div class="rollback-batch-entry">
      <div class="header">
        <table>
          <thead>
            <tr>
              <th>{{ $t('待回收集群') }}</th>
              <th>{{ $t('回收到新机器') }}</th>
              <th>{{ $t('备份源') }}</th>
              <th>{{ $t('回档类型') }}</th>
              <th>{{ $t('回档DB名') }}</th>
              <th>{{ $t('回档表名') }}</th>
              <th>{{ $t('忽略DB名') }}</th>
              <th>{{ $t('忽略表名') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Gamesever.edb.db</td>
              <td>127.0.0.17</td>
              <td>{{ $t('本地备份') }}</td>
              <td>{{ $t('回到档指定时间_Time', [demoDateTime]) }}</td>
              <td>null</td>
              <td>null</td>
              <td>null</td>
              <td>
                <span>null</span>
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
          style="height: 320px; margin: 12px 0 30px"
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
        <span v-if="inputClusterErrorStack.length > 0">
          <span v-if="inputInvalidStack.length > 0">；</span>
          <span>{{ $t('n处目标集群不存在', [inputClusterErrorStack.length]) }}</span>
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
    clusterData: {
      id: number;
      domain: string;
      cloudId: number;
    };
    rollbackIp: string;
    backupSource: string;
    backupid: number;
    rollbackTime: string;
    databases: string[];
    tables: string[];
    databasesIgnore: string[];
    tablesIgnore: string[];
  }
</script>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { queryClusters } from '@services/source/mysqlCluster';

  import { useGlobalBizs } from '@stores';

  import { ipv4 } from '@common/regex';

  import { execCopy } from '@/utils';


  interface IInputParse {
    domain: string,
    rollbackIp: string,
    backupSource: string,
    rollbackTime: string,
    databases: string,
    databasesIgnore: string,
    tables: string,
    tablesIgnore: string,
  }

  type RealDataMap = Record<string, {
    id: number,
    bk_cloud_id: number
  }>

  interface Props {
    isShow: boolean;
  }
  interface Emits {
    (e: 'update:isShow', value: boolean): void;
    (e: 'change', value: Array<IValue>): void;
  }

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const getInputTextList = (list: Array<IInputParse>) => list.map(item => [
    item.domain,
    item.rollbackIp,
    item.backupSource,
    item.rollbackTime,
    item.databases,
    item.tables,
    item.databasesIgnore,
    item.tablesIgnore,
  ].join('    '));

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const placeholder = t('请分别输入集群_起止时间_目标库_目标表_忽略库_忽略表_多个对象_换行分隔');

  const matchReg = /([^ ]+) +([^ ]+) +(local) +((?:[\d-]+ [\d:]+)|(?:\d+)) +([^ ]+) +([^ ]+) +([^ ]+) +([^ ]+)$/;

  const inputRef = ref();
  const isChecking = ref(false);
  const localValue = ref('');

  const inputInvalidStack = ref<Array<IInputParse>>([]);
  const inputErrorStack = ref<Array<IInputParse>>([]);
  const inputClusterErrorStack = ref<Array<IInputParse>>([]);

  const demoDateTime = dayjs().format('YYYY-MM-DD HH:mm:ss');

  const handleCopy = () => {
    execCopy(`${[
      'Gamesever.edb.db',
      '127.0.0.17',
      'local',
      demoDateTime,
      'null',
      'null',
      'null',
      'null',
    ].join('    ')}\n`);
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
      const match = recordItem.match(matchReg);
      if (!match) {
        errorList.push({
          domain: recordItem,
          rollbackIp: '',
          backupSource: '',
          rollbackTime: '',
          databases: '',
          tables: '',
          databasesIgnore: '',
          tablesIgnore: '',
        });
        return;
      }
      const [
        inputText,
        domain,
        rollbackIp,
        backupSource,
        rollbackTime,
        databases,
        tables,
        databasesIgnore,
        tablesIgnore,
      ] = match;

      const payload = {
        domain,
        rollbackIp,
        backupSource,
        rollbackTime,
        databases,
        tables,
        databasesIgnore,
        tablesIgnore,
      };

      // 集群格式不正确
      if (!/^\w+(:\d+)?/.test(domain)) {
        invalidList.push(payload);
        return;
      }
      // IP 格式正确
      if (!ipv4.test(rollbackIp)) {
        invalidList.push(payload);
        return;
      }
      // // 备份源类型不对应
      // if (backupSource === 'remote' && !/^\d+$/.test(rollbackTime)) {
      //   invalidList.push(payload);
      //   return;
      // }

      validList.push(payload);
    });

    isChecking.value = true;
    const clusterFilters = validList.map(item => ({
      immute_domain: item.domain,
    }));

    queryClusters({
      cluster_filters: clusterFilters,
      bk_biz_id: currentBizId,
    })
      .then((data) => {
        const realDataMap = data.reduce((result, item) => ({
          ...result,
          [item.master_domain]: {
            id: item.id,
            bk_cloud_id: item.bk_cloud_id,
          },
        }), {} as RealDataMap);

        const resultList: Array<IValue> = [];
        const clusterErrorList: Array<IInputParse> = [];

        validList.forEach((item) => {
          if (!realDataMap[item.domain]) {
            clusterErrorList.push(item);
          } else {
            const {
              rollbackIp,
              backupSource,
              rollbackTime,
              databases,
              tables,
              databasesIgnore,
              tablesIgnore,
            } = item;

            const getListValue = (str: string) => {
              if (str === 'null') {
                return [];
              }
              return str.split(',');
            };

            const isRollbackTime = !/^\d+$/.test(rollbackTime);

            resultList.push({
              clusterData: {
                id: realDataMap[item.domain].id,
                domain: item.domain,
                cloudId: realDataMap[item.domain].bk_cloud_id,
              },
              rollbackIp,
              backupSource,
              backupid: isRollbackTime ? 0 : Number(rollbackTime),
              rollbackTime: isRollbackTime ? rollbackTime : '',
              databases: getListValue(databases),
              tables: getListValue(tables),
              databasesIgnore: getListValue(databasesIgnore),
              tablesIgnore: getListValue(tablesIgnore),
            });
          }
        });
        inputInvalidStack.value = invalidList;
        inputErrorStack.value = errorList;
        inputClusterErrorStack.value = clusterErrorList;
        if (invalidList.length < 1
          && errorList.length < 1
          && clusterErrorList.length < 1) {
          emits('change', resultList);
          handleClosed();
        } else {
          const renderListValue = (arr: string[]) => {
            if (arr.length < 1) {
              return '-';
            }
            return arr.join(',');
          };
          localValue.value = _.filter([
            ...invalidList.map(item => getInputTextList([item])),
            ...errorList.map(item => getInputTextList([item])),
            ...clusterErrorList.map(item => getInputTextList([item])),
            ...resultList.map(item => [
              item.clusterData.domain,
              item.rollbackIp,
              item.backupSource,
              item.rollbackTime,
              renderListValue(item.databases),
              renderListValue(item.tables),
              renderListValue(item.databasesIgnore),
              renderListValue(item.tablesIgnore),
            ].join('    ')),
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
    inputClusterErrorStack.value = [];
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
    const clusterErrorText = getInputTextList(inputClusterErrorStack.value).join('\n');

    const startIndex = invalidText.length > 0 ? invalidText.length + 1 : 0;
    $inputEl.selectionStart = startIndex;
    $inputEl.selectionEnd = startIndex + clusterErrorText.length;
  };
</script>
<style lang="less">
  .rollback-batch-entry {
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
