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
  <div class="domain-table">
    <DbOriginalTable
      class="custom-edit-table"
      :columns="columns"
      :data="tableData"
      :empty-text="t('请选择业务')" />
    <InstanceSelector
      :key="instanceSelectorKey"
      v-model:is-show="isShowInstanceSelector"
      :cluster-types="['RedisHost']"
      :selected="selectedHostList"
      :tab-list-config="tabListConfig"
      @change="handleInstancesChange" />
  </div>
</template>

<script setup lang="tsx">
  import type { Column } from 'bkui-vue/lib/table/props';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import RedisMachineModel from '@services/model/redis/redis-machine';
  import { getRedisClusterList, getRedisMachineList } from '@services/source/redis'

  import { ClusterTypes } from '@common/const'
  import { ipv4, nameRegx } from '@common/regex';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType
  } from '@components/instance-selector/Index.vue';

  import ClusterNameBatchEdit from './components/ClusterNameBatchEdit.vue';
  import DatabasesBatchEdit from './components/DatabasesBatchEdit.vue';
  import HostBatchEdit from './components/HostBatchEdit.vue'

  export interface Domain {
    cluster_name: string;
    databases: number;
    masterHost: {
      ip: string;
      bk_cloud_id: number;
      bk_host_id: number;
    }
    slaveHost: {
      ip: string;
      bk_cloud_id: number;
      bk_host_id: number;
    }
  }

  interface Props {
    isAppend: boolean;
    appAbbr: string;
    port: number;
    cloudId: string | number;
    maxMemory: string;
    cityInfo: {
      cityCode: string,
      cityName: string
    }
    portType: string | number[];
  }

  interface Emits {
    (e: 'hostChange', fieldName: string, value: string, index: number): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>()
  const domains = defineModel<Array<Domain>>('domains', {
    default: () => [],
  });

  const { t } = useI18n();

  const rules = {
    cluster_name: [
      {
        required: true,
        message: t('必填项'),
        trigger: 'change',
      },
      {
        message: t('最大长度为m', { m: 63 }),
        trigger: 'blur',
        validator: (value: string) => value.length <= 63,
      },
      {
        message: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
        trigger: 'blur',
        validator: (value: string) => nameRegx.test(value),
      },
      {
        message: t('集群重复'),
        trigger: 'blur',
        validator: (value: string) => clusterNameList.value.filter(item => item === value).length < 2,
      },
    ],
    'masterHost.ip': [
      {
        required: true,
        message: t('必填项'),
        trigger: 'change',
      },
      {
        validator: (value: string) => ipv4.test(value),
        message: t('目标主库主机格式不正确'),
      },
      // {
      //   validator: (value: string) => masterHostIpList.value.filter(item => item === value).length < 2,
      //   message: t('目标主机重复'),
      // },
      {
        validator: (value: string) =>
          getRedisMachineList({
            ip: value,
            instance_role: 'redis_master',
            bk_cloud_id: props.cloudId as number,
            bk_city_name: props.cityInfo.cityName,
            cluster_type: ClusterTypes.REDIS_INSTANCE
          }).then((data) => {
            const redisMachineList = data.results;
            if (redisMachineList.length < 1) {
              return false;
            }
            return true;
          }),
        message: t('目标主库主机不存在'),
      },
    ],
    'slaveHost.ip': [
      {
        required: true,
        message: t('必填项'),
        trigger: 'change',
      },
    ]
  };

  const columns = computed(() => {
    const baseColums: Column[] = [
      {
        type: 'seq',
        label: t('序号'),
        width: 60,
      },
      {
        label: () => (
          <div class='table-custom-label'>
            { t('主访问入口') }
            <span class="required-mark">*</span>
            {
              tableData.value.length !== 0 && (
                <span v-bk-tooltips={t('批量编辑')}>
                  <ClusterNameBatchEdit
                    appAbbr={props.appAbbr}
                    onChange={handleBatchClusterName} />
                </span>
              )
            }
          </div>
        ),
        field: 'cluster_name',
        minWidth: 300,
        render: ({ index }: { index: number }) => (
          <div class="cluster_name">
            <div class="mr-4">ins.</div>
            <bk-form-item
              class="cell-item"
              errorDisplayType="tooltips"
              property={`details.infos.${index}.cluster_name`}
              key={index}
              rules={rules.cluster_name}
              label-width={0}>
              <bk-input
                model-value={domains.value[index]?.cluster_name}
                style="width: 200px"
                onChange={(value: string) => handleChangeCellValue(value, index, 'cluster_name')}
              />
            </bk-form-item>
            {
              typeof props.portType === 'string' ?
                <div class="ml-4">.{ props.appAbbr }.db{props.isAppend ? '' : `#${props.portType === 'increment' ? props.port + index : props.port }`}</div>
                :
                <div class="ml-4">.{ props.appAbbr }.db{props.isAppend ? '' : `#${props.portType.length === tableData.value.length ? props.portType[index] : ''}`}</div>
            }
          </div>
        ),
      },
      // {
      //   label: t('从域名'),
      //   field: 'slave_domain',
      //   minWidth: 260,
      //   render: ({ data, index }: { data: Domain, index: number }) => `ins-slave.${data.cluster_name}.${props.appAbbr}.db${props.isAppend ? '' : `#${props.port + index}`}`
      // },
      {
        label: () => (
          <div class='table-custom-label'>
            Databases
            <span class="required-mark">*</span>
            {
              tableData.value.length !== 0 && (
                <span v-bk-tooltips={t('批量编辑')}>
                  <DatabasesBatchEdit onChange={handleBatchDatabases} />
                </span>
              )
            }
          </div>
        ),
        field: 'databases',
        width: 150,
        render: ({ index }: { index: number }) => (
          <bk-form-item
            class="cell-item"
            errorDisplayType="tooltips"
            property={`details.infos.${index}.databases`}
            key={index}
            label-width={0}>
            <bk-input
              model-value={domains.value[index]?.databases}
              type="number"
              min={2}
              max={64}
              placeholder={t('范围 2～64')}
              onChange={(value: string) => handleChangeCellValue(value, index, 'databases')}
            />
          </bk-form-item>
        ),
      },
    ];
    const newColums: Column[] = [
      {
        label: 'Maxmemory',
        field: 'maxmemory',
        width: 200,
        render: () => props.maxMemory
      }
    ]
    const appendColums: Column[] = [
      {
        label: () => (
          <div class='table-custom-label'>
            { t('待部署主库主机') }
            <span class="required-mark">*</span>
            {
              tableData.value.length !== 0 && (
                <span v-bk-tooltips={t('批量编辑')}>
                  <HostBatchEdit
                    cloudId={props.cloudId}
                    cityName={props.cityInfo.cityName}
                    onChange={handleBatchHost} />
                </span>
              )
            }
          </div>
        ),
        field: 'masterHost',
        width: 220,
        render: ({ index }: { index: number }) => (
          <bk-form-item
            class="cell-item master-ip-input-item"
            errorDisplayType="tooltips"
            property={`details.infos.${index}.masterHost.ip`}
            rules={rules['masterHost.ip']}
            key={index}
            label-width={0}>
            <bk-input
              model-value={domains.value[index]?.masterHost.ip}
              placeholder={t('请输入或选择')}
              onChange={(value: string) => handleHostIpChange(value, index)}>
              {{
                suffix: () => (
                  <bk-button
                    text
                    class="mr-8"
                    onClick={() => handleInstancesSelectorShow(index)}>
                    <db-icon
                      v-bk-tooltips={t("选择主机")}
                      type="host-select" />
                  </bk-button>
                )
              }}
            </bk-input>
          </bk-form-item>
        ),
      },
      {
        label: t('待部署从库主机'),
        field: 'slaveHost',
        width: 220,
        render: ({ index }: { index: number }) => (
          <bk-form-item
            class="cell-item"
            errorDisplayType="tooltips"
            property={`details.infos.${index}.slaveHost.ip`}
            rules={rules['slaveHost.ip']}
            key={index}
            label-width={0}>
            <bk-input
              readonly
              model-value={domains.value[index]?.slaveHost.ip}
              placeholder={t('选择主库主机后自动生成')}
            />
          </bk-form-item>
        ),
      },
    ]

    baseColums.push(...(props.isAppend ? appendColums : newColums))

    return baseColums
  })

  const isShowInstanceSelector = ref(false);
  const instanceSelectorIndex = ref(-1)

  const selectedHostList = shallowRef({ RedisHost: [] } as InstanceSelectorValues<IValue>);

  const tabListConfig = computed(() => ({
    RedisHost: [
      {
        topoConfig: {
          getTopoList: (params: ServiceParameters<typeof getRedisClusterList>) => getRedisClusterList({
            ...params,
            region: props.cityInfo.cityCode
          }),
          totalCountFunc: (dataList: RedisModel[]) => {
            const ipSet = new Set<string>()
            dataList.forEach(dataItem => dataItem.redis_master.forEach(masterItem => ipSet.add(masterItem.ip)))
            return ipSet.size
          }
        },
        tableConfig: {
          getTableList: (params: Record<string, any>) => getRedisMachineList({
            ...params,
            bk_cloud_id: props.cloudId as number,
            bk_city_name: props.cityInfo.cityName,
            cluster_type: ClusterTypes.REDIS_INSTANCE
          }),
          disabledRowConfig: {
            handler: (data: RedisMachineModel) => data.isUnvailable,
            tip: t('异常主机不可用')
          }
        }
      },
      {
        tableConfig: {
          getTableList: (params: Record<string, any>) => getRedisMachineList({
            ...params,
            bk_cloud_id: props.cloudId as number,
            bk_city_name: props.cityInfo.cityName,
            cluster_type: ClusterTypes.REDIS_INSTANCE
          }),
          disabledRowConfig: {
            handler: (data: RedisMachineModel) => data.isUnvailable,
            tip: t('异常主机不可用')
          }
        },
        manualConfig: {
          checkInstances: (params: Record<string, any>) => getRedisMachineList({
            ...params,
            bk_cloud_id: props.cloudId as number,
            bk_city_name: props.cityInfo.cityName,
            cluster_type: ClusterTypes.REDIS_INSTANCE
          })
        }
      },
    ]}) as unknown as Record<'RedisHost', PanelListType>
  );

  // 没有 appName 则不展示 table 数据
  const tableData = computed(() => {
    if (props.appAbbr) {
      return domains.value;
    }
    return [];
  });

  const clusterNameList = computed(() => tableData.value.map(item => item.cluster_name));
  // const masterHostIpList = computed(() => tableData.value.map(item => item.masterHost.ip));

  const instanceSelectorKey = computed(() => `${props.cloudId}-${props.cityInfo.cityName}`)

  const handleBatchClusterName = (values: string[]) => {
    if (values.length !== 0) {
      const newDomains = domains.value;
      newDomains.forEach((item, index) => {
        if (values[index] !== undefined) {
          newDomains[index].cluster_name = values[index];
        }
      });
      domains.value = newDomains;
    }
  };

  const handleBatchDatabases = (value: number) => {
    const newDomains = domains.value;
    newDomains.map(item => Object.assign(item, { databases: value }))
  }

  const handleBatchHost = (values: string[]) => {
    if (values.length !== 0) {
      const newDomains = domains.value;
      newDomains.forEach((item, index) => {
        if (values[index] !== undefined) {
          newDomains[index].masterHost.ip = values[index];
          emits('hostChange',  `details.infos.${index}.masterHost.ip`, values[index], index)
        }
      });
      domains.value = newDomains;
    }
  };

  const handleChangeCellValue = (value: string, index: number, fieldName: string) => {
    const newDomains = _.cloneDeep(domains.value);
    Object.assign(newDomains[index], { [fieldName]: value} );
    domains.value = newDomains;
  };

  const handleHostIpChange = (value: string, index: number) => {
    const newDomains = _.cloneDeep(domains.value);
    Object.assign(newDomains[index].masterHost, {
      ip: value
    });
    domains.value = newDomains;
    emits('hostChange',  `details.infos.${index}.masterHost.ip`, value, index)
  }

  const handleInstancesSelectorShow = (index: number) => {
    isShowInstanceSelector.value = true
    instanceSelectorIndex.value = index
  }

  const handleInstancesChange = (selectedValues: InstanceSelectorValues<IValue>) => {
    const { ip } = selectedValues.RedisHost[0]
    const newDomains = _.cloneDeep(domains.value);
    Object.assign(newDomains[instanceSelectorIndex.value].masterHost, {
      ip
    });
    domains.value = newDomains;
    emits('hostChange',  `details.infos.${instanceSelectorIndex.value}.masterHost.ip`, ip, instanceSelectorIndex.value)
    instanceSelectorIndex.value = -1
  }
</script>

<style lang="less" scoped>
  .domain-table {
    :deep(.bk-table) {
      .bk-form-content {
        margin-left: 0 !important;
      }

      tr:hover {
        .bk-input {
          background-color: #f5f7fa !important;
        }
      }
    }

    :deep(.table-custom-label) {
      display: flex;
      align-items: center;
    }

    :deep(.domain-address) {
      display: flex;
      align-items: center;

      > span {
        flex-shrink: 0;
      }

      .cell-item {
        margin-bottom: 0;

        .bk-form-label {
          display: none;
        }
      }
    }

    :deep(.required-mark) {
      margin: 0 2px 0 6px;
      color: #ea3636;
    }

    :deep(.cluster_name) {
      display: flex;
      align-items: center;
    }

    :deep(.bk-form-item) {
      margin-bottom: 0;
    }

    :deep(.master-ip-input-item) {
      .bk-form-error-tips {
        right: 26px;
      }
    }
  }
</style>
