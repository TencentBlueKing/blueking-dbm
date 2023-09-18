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
  <SuccessView
    v-if="ticketId"
    :steps="[{
      title: $t('单据审批'),
      status: 'loading',
    }, {
      title: $t('重建从库_执行'),
    }]"
    :ticket-id="ticketId"
    :title="$t('重建从库任务提交成功')"
    @close="handleCloseSuccess" />
  <SmartAction
    v-else
    class="slave-rebuild">
    <BkAlert
      closable
      :title="$t('重建从库_原机器或新机器重新同步数据及权限_并且将域名解析指向同步好的机器')" />
    <div class="slave-rebuild-types">
      <strong class="slave-rebuild-types-title">
        {{ $t('重建类型') }}
      </strong>
      <div class="mt-8 mb-8">
        <CardCheckbox
          checked
          :desc="$t('在原主机上进行故障从库实例重建')"
          icon="rebuild"
          :title="$t('原地重建')" />
      </div>
    </div>
    <BkButton
      class="slave-rebuild-batch"
      @click="() => isShowBatchInput = true">
      <i class="db-icon-add" />
      {{ $t('批量录入') }}
    </BkButton>
    <ToolboxTable
      ref="toolboxTableRef"
      class="mb-32"
      :columns="columns"
      :data="tableData"
      :max-height="tableMaxHeight"
      @add="handleAddItem"
      @remove="handleRemoveItem" />
    <template #action>
      <BkButton
        class="mr-8 w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ $t('提交') }}
      </BkButton>
      <BkButton
        class="w-88"
        :disabled="isSubmitting"
        @click="handleReset">
        {{ $t('重置') }}
      </BkButton>
    </template>
  </SmartAction>
  <BatchInput
    v-model:is-show="isShowBatchInput"
    @change="handleBatchInput" />
  <InstanceSelector
    v-model:is-show="isShowInstanceSelecotr"
    :panel-list="['tendbha', 'manualInput']"
    role="slave"
    @change="handleInstancesChange" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { checkInstances } from '@services/clusters';
  import { createTicket } from '@services/ticket';
  import type { InstanceInfos } from '@services/types/clusters';

  import { useInfo, useTableMaxHeight } from '@hooks';

  import { TicketTypes } from '@common/const';
  import { ipPort } from '@common/regex';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';
  import InstanceSelector, {
    type InstanceSelectorValues,
  } from '@components/instance-selector/Index.vue';
  import BatchEdit from '@components/mysql-toolbox/BatchEdit.vue';
  import SuccessView from '@components/mysql-toolbox/Success.vue';
  import ToolboxTable from '@components/mysql-toolbox/ToolboxTable.vue';

  import { generateId } from '@utils';

  import BatchInput from './components/BatchInput.vue';

  import { useGlobalBizs } from '@/stores';
  import type { TableProps } from '@/types/bkui-vue';

  interface TableItem {
    instance_address: string,
    slave: {
      bk_biz_id: number,
      bk_cloud_id: number,
      bk_host_id: number,
      ip: string,
      port: number
    },
    cluster_id: number,
    backup_source: string,
    uniqueId: string
  }
  interface TableColumnData {
    index: number,
    data: TableItem
  }

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const tableMaxHeight = useTableMaxHeight(448);

  const ticketId = ref(0);
  const toolboxTableRef = ref();
  const isShowBatchInput = ref(false);
  const isSubmitting = ref(false);
  const isShowInstanceSelecotr = ref(false);
  const instanceMap: Map<string, InstanceInfos> = reactive(new Map());
  const tableData = ref<Array<TableItem>>([getTableItem()]);
  const backupRules = [
    {
      validator: (value: string) => !!value,
      message: t('请选择'),
      trigger: 'blur',
    },
  ];
  const backupList = [
    {
      value: 'local',
      label: t('本地备份'),
    },
  ];
  const columns: TableProps['columns'] = [
    {
      label: () => (
        <span>
          { t('目标从库实例') }
          <db-icon type="batch-host-select" onClick={() => isShowInstanceSelecotr.value = true} />
        </span>
      ),
      field: 'instance_address',
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          key={`${data.uniqueId}_instance_address`}
          error-display-type="tooltips"
          rules={getRules(data)}
          property={`${index}.instance_address`}>
          <bk-input
            v-model={[data.instance_address, ['trim']]}
            placeholder={t('请输入IP_Port')}
            onBlur={hanldeDomainBlur.bind(null, index)} />
        </bk-form-item>
      ),
    },
    {
      label: t('所属集群'),
      field: 'cluster',
      showOverflowTooltip: false,
      render: ({ data }: TableColumnData) => {
        const instanceInfo = instanceMap.get(data.instance_address);
        if (!instanceInfo) {
          return <p class="placeholder">{ t('根据实例生成') }</p>;
        }
        return (
          <div class="text-overflow pl-10 pr-10" v-overflow-tips>{instanceInfo.master_domain}</div>
        );
      },
    },
    {
      label: () => (
        <span>
          { t('备份来源') }
          <BatchEdit
            title={t('批量编辑备份来源')}
            width={420}
            tooltips={t('批量编辑')}
            validator={validatorBatchSelect.bind(null, t('请选择备份来源'))}
            onChange={handleBatchBackupChange}>
            {{
              default: ({ state }: any) => (
                <bk-select
                  v-model={state.value}
                  list={backupList}
                  clearable={false}
                  popover-options={{ boundary: 'parent', disableTeleport: true }}
                />
              ),
            }}
          </BatchEdit>
        </span>
      ),
      field: 'backup_source',
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          key={`${data.uniqueId}_backup_source`}
          error-display-type="tooltips"
          rules={backupRules}
          property={`${index}.backup_source`}>
          <bk-select v-model={data.backup_source} list={backupList} clearable={false}></bk-select>
        </bk-form-item>
      ),
    },
  ];

  /**
   * 获取表格数据
   */
  function getTableItem(): TableItem {
    return {
      instance_address: '',
      slave: {
        bk_biz_id: 0,
        bk_cloud_id: 0,
        bk_host_id: 0,
        ip: '',
        port: 0,
      },
      cluster_id: 0,
      backup_source: '',
      uniqueId: generateId('REBUILD_SLAVE_'),
    };
  }

  /**
   * 设置集群 id
   */
  function hanldeDomainBlur(index: number) {
    const item = tableData.value[index];
    const info = instanceMap.get(item.instance_address);
    item.cluster_id = info?.cluster_id ?? 0;
  }

  /**
   * 获取目标从库实例校验规则
   */
  function getRules(data: TableItem) {
    return [
      {
        validator: (inst: string) => ipPort.test(inst),
        message: t('请输入合法IP_Port'),
        trigger: 'blur',
      },
      {
        validator: (value: string) => verifyInstance(data, value),
        message: t('实例不存在'),
        trigger: 'blur',
      },
      {
        validator: (value: string) => !tableData.value.find(item => (
          item.uniqueId !== data.uniqueId
          && item.instance_address === value
        )),
        message: t('目标从库在修改列表中已存在'),
        trigger: 'blur',
      },
    ];
  }

  /**
   * 备份来源批量选择校验
   */
  function validatorBatchSelect(errorText: string, value: string) {
    return {
      isPass: !!value,
      errorText,
    };
  }

  /**
   * 备份来源批量选择校验
   */
  function handleBatchBackupChange(value: string) {
    for (const item of tableData.value) {
      item.backup_source = value;
    }
  }

  /**
   * 查询实例信息
   */
  function fetchInstanceInfos() {
    const instances = tableData.value.map(item => item.instance_address).filter(inst => ipPort.test(inst));
    return checkInstances(globalBizsStore.currentBizId, { instance_addresses: instances })
      .then((res) => {
        for (const item of res) {
          const { ip, port } = item;
          instanceMap.set(`${ip}:${port}`, item);

          // 设置集群 id
          const list = tableData.value.filter(tableItem => tableItem.instance_address === `${item.ip}:${item.port}`);
          for (const tableItem of list) {
            tableItem.cluster_id = item.cluster_id;
            tableItem.slave = {
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              bk_biz_id: globalBizsStore.currentBizId,
              ip,
              port,
            };
          }
        }
        return res;
      });
  }

  /**
   * 校验实例是否存在
   */
  function verifyInstance(data: TableItem, value: string) {
    // 已经查询过且存在的实例
    const curInstanceInfo = instanceMap.get(data.instance_address);
    if (curInstanceInfo?.cluster_id) {
      return true;
    }

    return fetchInstanceInfos().then(() => Boolean(instanceMap.get(value)?.cluster_id));
  }

  /**
   * 批量添加若只有一行且为空则清空
   */
  function clearEmptyTableData() {
    if (tableData.value.length === 1) {
      const data = tableData.value[0];
      if (!data.instance_address && !data.backup_source) {
        tableData.value = [];
      }
    }
  }

  /**
   * 批量录入
   */
  async function handleBatchInput(list: Array<{ instance: string, backup: string }>) {
    const formatList = list.map(item => ({
      ...getTableItem(),
      instance_address: item.instance,
      backup_source: 'local', // TODO: 目前只有"本地备份"，后续扩展需要根据返回 backup 文案判断类型
    }));
    clearEmptyTableData();
    tableData.value.push(...formatList);
    window.changeConfirm = true;

    try {
      await fetchInstanceInfos();
    } catch (e) {
      console.log(e);
    }

    // 触发表格校验
    toolboxTableRef.value.validate();
  }

  function handleAddItem(index: number) {
    tableData.value.splice(index + 1, 0, getTableItem());
  }

  function handleRemoveItem(index: number) {
    tableData.value.splice(index, 1);
  }

  function handleReset() {
    useInfo({
      title: t('确认重置表单内容'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        tableData.value = [getTableItem()];
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
    });
  }

  async function handleInstancesChange(data: InstanceSelectorValues) {
    const newList = [];
    const existList = tableData.value.map(item => item.instance_address);
    for (const item of data.tendbha) {
      const {
        instance_address,
        cluster_id,
        ip,
        port,
        bk_cloud_id,
        bk_host_id,
      } = item;
      if (!existList.includes(instance_address)) {
        newList.push({
          ...getTableItem(),
          instance_address,
          cluster_id,
          slave: {
            bk_cloud_id,
            bk_host_id,
            ip,
            port,
            bk_biz_id: globalBizsStore.currentBizId,
          },
        });
      }
    }
    if (newList.length === 0) return;

    clearEmptyTableData();
    tableData.value.push(...newList);
    window.changeConfirm = true;

    try {
      await fetchInstanceInfos();
    } catch (e) {
      console.log(e);
    }
  }

  function handleSubmit() {
    toolboxTableRef.value.validate()
      .then(() => {
        isSubmitting.value = true;
        const params = {
          ticket_type: TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE,
          bk_biz_id: globalBizsStore.currentBizId,
          details: {
            infos: tableData.value.map(item => ({
              slave: item.slave,
              cluster_id: item.cluster_id,
              backup_source: item.backup_source,
            })),
          },
        };
        createTicket(params)
          .then((res) => {
            ticketId.value = res.id;
            tableData.value = [getTableItem()];
            nextTick(() => {
              window.changeConfirm = false;
            });
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      });
  }

  function handleCloseSuccess() {
    ticketId.value = 0;
  }
</script>

<style lang="less" scoped>
  .slave-rebuild {
    height: 100%;
    overflow: hidden;

    .slave-rebuild-batch {
      margin: 16px 0;

      .db-icon-add {
        margin-right: 4px;
        color: @gray-color;
      }
    }

    .slave-rebuild-types {
      margin-top: 24px;

      .slave-rebuild-types-title {
        position: relative;
        font-size: @font-size-mini;
        color: @title-color;

        &::after {
          position: absolute;
          top: 2px;
          right: -8px;
          color: @danger-color;
          content: "*";
        }
      }
    }
  }
</style>
