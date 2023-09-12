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
      title: $t('DB实例权限克隆_执行'),
    }]"
    :ticket-id="ticketId"
    :title="$t('DB实例权限克隆任务提交成功')"
    @close="handleCloseSuccess" />
  <SmartAction
    v-else
    class="clone-instance">
    <BkAlert
      closable
      :title="$t('DB权限克隆_DB实例IP替换时_克隆原实例的所有权限到新实例中')" />
    <BkButton
      class="clone-instance__batch"
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
    @change="handleInstancesChange" />
</template>

<script setup lang="tsx">
  import type FormItem from 'bkui-vue/lib/form/form-item';
  import { useI18n } from 'vue-i18n';

  import { checkInstances } from '@services/clusters';
  import { precheckPermissionClone } from '@services/permission';
  import { createTicket } from '@services/ticket';
  import type { InstanceInfos } from '@services/types/clusters';

  import { useInfo, useTableMaxHeight } from '@hooks';

  import { TicketTypes } from '@common/const';
  import { ipPort } from '@common/regex';

  import InstanceSelector, {
    type InstanceSelectorValues,
  } from '@components/instance-selector/Index.vue';

  import { generateId, messageError } from '@utils';

  import BatchInput from './components/BatchInput.vue';

  import SuccessView from '@/components/mysql-toolbox/Success.vue';
  import ToolboxTable from '@/components/mysql-toolbox/ToolboxTable.vue';
  import { useGlobalBizs } from '@/stores';
  import type { TableProps } from '@/types/bkui-vue';

  type FormItemInstance = InstanceType<typeof FormItem>;
  interface TableItem {
    source: string,
    target: string,
    uniqueId: string
  }
  interface TableColumnData {
    index: number,
    data: TableItem
  }

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const tableMaxHeight = useTableMaxHeight(334);

  const ticketId = ref(0);
  const toolboxTableRef = ref();
  const isShowBatchInput = ref(false);
  const isSubmitting = ref(false);
  const isShowInstanceSelecotr = ref(false);
  const instanceMap: Map<string, InstanceInfos> = reactive(new Map());
  const tableData = ref<Array<TableItem>>([getTableItem()]);
  const originInstanceRules = [
    {
      validator: (inst: string) => {
        if (inst === '') return false;

        const infos = inst.split(':');
        if (infos.length !== 3) return false;

        // 判断是否为合法管控区域
        if (/^\d+$/.test(infos[0]) === false) return false;
        // 判断是否为合法实例
        if (ipPort.test(`${infos[1]}:${infos[2]}`) === false) return false;

        return true;
      },
      message: t('请输入合法管控区域_IP_Port'),
      trigger: 'blur',
    },
    {
      validator: verifyInstance,
      message: t('实例不存在'),
      trigger: 'blur',
    },
  ];
  const columns: TableProps['columns'] = [
    {
      label: () => (
        <span>
          { t('源实例') }
          <db-icon type="batch-host-select" onClick={() => isShowInstanceSelecotr.value = true} />
        </span>
      ),
      field: 'source',
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          key={`${data.uniqueId}_source`}
          error-display-type="tooltips"
          ref={setFormItemRefs.bind(null, 'source')}
          rules={originInstanceRules}
          property={`${index}.source`}>
          <bk-input v-model={[data.source, ['trim']]} placeholder={t('请输入xx', [t('管控区域_IP_Port')])} />
        </bk-form-item>
      ),
    },
    {
      label: t('所属集群'),
      field: 'cluster',
      showOverflowTooltip: false,
      render: ({ data }: TableColumnData) => {
        const instanceInfo = instanceMap.get(data.source);
        if (!instanceInfo) {
          return <p class="placeholder">{ t('输入源实例后自动生成') }</p>;
        }
        return (
          <div class="text-overflow pl-10 pr-10" v-overflow-tips>{instanceInfo.master_domain}</div>
        );
      },
    },
    {
      label: t('新实例'),
      field: 'target',
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          key={`${data.uniqueId}_target`}
          error-display-type="tooltips"
          ref={setFormItemRefs.bind(null, 'target')}
          rules={getNewInstanceRules(data)}
          property={`${index}.target`}>
          <bk-input v-model={[data.target, ['trim']]} placeholder={t('请输入单个IP_Port')} />
        </bk-form-item>
      ),
    },
  ];
  // 设置 target|source form-item
  const formItemRefs = reactive({
    target: [] as FormItemInstance[],
    source: [] as FormItemInstance[],
  });
  function setFormItemRefs(key: 'target' | 'source', vueInstance: FormItemInstance) {
    if (vueInstance) {
      const refs = formItemRefs[key];
      const refProperties = refs.map(item => item.$props.property);
      const curProperty = vueInstance.$props.property;
      if (!refProperties.includes(curProperty)) {
        formItemRefs[key].push(vueInstance);
      }
    }
  }

  const getOriginlInstanceInfos = (value: string) => {
    const [cloudId, ip, port] = value.split(':');
    return {
      cloudId,
      ip,
      port,
      inst: `${ip}:${port}`,
    };
  };

  /**
   * 获取表格数据
   */
  function getTableItem(): TableItem {
    return {
      source: '',
      target: '',
      uniqueId: generateId('CLONE_INSTANCE_'),
    };
  }

  /**
   * 获取实例正则校验
   */
  function getNewInstanceRules(data: TableItem) {
    return [
      {
        validator: (inst: string) => ipPort.test(inst),
        message: t('请输入合法IP_Port'),
        trigger: 'blur',
      },
      {
        validator: (val: string) => {
          const targets = val.split('\n').map(value => value.trim());
          return targets.every(value => value !== getOriginlInstanceInfos(data.source).inst);
        },
        message: t('xx为源实例', [getOriginlInstanceInfos(data.source).inst]),
        trigger: 'blur',
      },
      {
        validator: async (value: string) => {
          const infos = instanceMap.get(data.source);
          // 还未校验源实例则先跳过新实例校验
          if (infos === undefined) return true;
          await verifyInstance(`${infos.bk_cloud_id}:${value}`);
          return Array.from(instanceMap.keys()).filter(key => key.includes(value)).length > 0;
        },
        message: t('实例不存在'),
        trigger: 'blur',
      },
      {
        validator: () => {
          const infos = instanceMap.get(data.source);
          // 还未校验源实例则先跳过新实例校验
          if (infos === undefined) return true;

          const instanceInfos = instanceMap.get(`${getOriginlInstanceInfos(data.source).cloudId}:${data.target}`);
          return instanceInfos !== undefined;
        },
        message: t('源实例IPxx跟新实例IPxx须在同一个管控区域', {
          source: getOriginlInstanceInfos(data.source).inst,
          target: data.target,
        }),
        trigger: 'blur',
      },
    ];
  }

  /**
   * 查询实例信息
   */
  function fetchInstanceInfos(instances: string[]) {
    return checkInstances(globalBizsStore.currentBizId, { instance_addresses: instances })
      .then((res) => {
        for (const item of res) {
          const { ip, port, bk_cloud_id: cloudId } = item;
          instanceMap.set(`${cloudId}:${ip}:${port}`, item);
        }
        return res;
      });
  }

  /**
   * 校验实例是否存在
   */
  function verifyInstance(value: string) {
    // 已经查询过且存在的实例
    const curInstanceInfo = instanceMap.get(value);
    if (curInstanceInfo !== undefined) {
      return true;
    }

    const instances: string[] = [];
    for (const item of tableData.value) {
      instances.push(getOriginlInstanceInfos(item.source).inst);
      instances.push(item.target);
    }
    return fetchInstanceInfos(instances.filter(inst => ipPort.test(inst.trim())))
      .then(() => instanceMap.get(value) !== undefined);
  }

  /**
   * 批量添加若只有一行且为空则清空
   */
  function clearEmptyTableData() {
    if (tableData.value.length === 1) {
      const data = tableData.value[0];
      if (Object.values({ ...data, uniqueId: '' }).every(value => !value)) {
        tableData.value = [];
      }
    }
  }

  /**
   * 批量录入
   */
  async function handleBatchInput(list: Array<{ source: string, target: string }>) {
    const formatList = list.map(item => ({
      ...getTableItem(),
      source: item.source,
      target: item.target,
    }));
    clearEmptyTableData();
    tableData.value.push(...formatList);
    window.changeConfirm = true;

    const hosts = list.reduce((hosts: string[], item) => hosts.concat([item.source, ...item.target.split('\n')]), []);

    try {
      await Promise.all([fetchInstanceInfos(hosts)]);
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
    const dataList = Object.values(data).reduce((res, items) => res.concat(items));
    const existList = tableData.value.map(item => item.source);
    for (const item of dataList) {
      const source = `${item.bk_cloud_id}:${item.instance_address}`;
      if (!existList.includes(source)) {
        newList.push({
          ...getTableItem(),
          source,
        });
      }
    }
    if (newList.length === 0) return;

    clearEmptyTableData();
    tableData.value.push(...newList);
    window.changeConfirm = true;

    try {
      await fetchInstanceInfos(newList.map(item => item.source));
    } catch (e) {
      console.log(e);
    }
  }

  function handleSubmit() {
    isSubmitting.value = true;
    toolboxTableRef.value.validate()
      .then(() => {
        precheckPermissionClone(globalBizsStore.currentBizId, {
          clone_type: 'instance',
          clone_cluster_type: 'mysql',
          clone_list: tableData.value.map((item) => {
            const infos = getOriginlInstanceInfos(item.source);
            return {
              source: infos.inst,
              target: item.target,
              cluster_domain: instanceMap.get(item.source)?.master_domain,
              bk_cloud_id: instanceMap.get(item.source)?.bk_cloud_id,
            };
          }),
        })
          .then((res) => {
            if (res.pre_check) {
              createTicket({
                ticket_type: TicketTypes.MYSQL_INSTANCE_CLONE_RULES,
                bk_biz_id: globalBizsStore.currentBizId,
                details: {
                  ...res,
                  clone_type: 'instance',
                },
              })
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
              return;
            }
            isSubmitting.value = false;
            messageError(res.message);
          })
          .catch(() => {
            isSubmitting.value = false;
          });
      })
      .catch(() => {
        isSubmitting.value = false;
      });
  }

  function handleCloseSuccess() {
    ticketId.value = 0;
  }
</script>

<style lang="less" scoped>
  .clone-instance {
    height: 100%;
    overflow: hidden;

    &__batch {
      margin: 16px 0;

      .db-icon-add {
        margin-right: 4px;
        color: @gray-color;
      }
    }
  }
</style>
