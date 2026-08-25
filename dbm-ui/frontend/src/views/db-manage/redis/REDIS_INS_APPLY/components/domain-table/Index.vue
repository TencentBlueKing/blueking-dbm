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
    <PrimaryTable
      class="custom-edit-table"
      :columns="columns"
      :data="tableData"
      :empty="t('请选择业务')"
      row-key="cluster_name" />
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
  import _ from 'lodash';
  import type { PrimaryTableCol } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import RedisMachineModel from '@services/model/redis/redis-machine';
  import { getRedisClusterList, getRedisMachineList } from '@services/source/redis';
  import { checkDomainRepeat } from '@services/source/ticket.tsx';

  import { ClusterTypes } from '@common/const';
  import { clusterNameFormatRegx, clusterNameSymbolRegx, ipv4 } from '@common/regex';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  import { getDomainStrategy } from '@views/db-manage/utils/getDomainPreview.ts';

  import ClusterNameBatchEdit from './components/ClusterNameBatchEdit.vue';
  import DatabasesBatchEdit from './components/DatabasesBatchEdit.vue';
  import HostBatchEdit from './components/HostBatchEdit.vue';

  export interface Domain {
    cluster_name: string;
    databases: number;
    masterHost: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
    slaveHost: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
  }

  interface Props {
    appAbbr: string;
    cityInfo: {
      city_code: string;
      city_name: string;
    };
    cloudId: string | number;
    isAppend: boolean;
    maxMemory: string;
    port: number;
    portType: string | number[];
  }

  type Emits = (e: 'hostChange', fieldName: string, value: string, index: number) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const domains = defineModel<Array<Domain>>('domains', {
    default: () => [],
  });

  const { t } = useI18n();

  const rules = {
    cluster_name: [
      {
        message: '',
        required: true,
        trigger: 'blur',
        validator: (val: string) => !!val,
      },
      // {
      //   message: t('最大长度为m', { m: 63 }),
      //   trigger: 'blur',
      //   validator: (value: string) => value.length <= 63,
      // },
      {
        message: t('不能以连字符开头或结尾'),
        trigger: 'blur',
        validator: (val: string) => clusterNameFormatRegx.test(val),
      },
      {
        message: t('格式不正确，请勿使用中文、大写、空格、下划线或特殊符号'),
        trigger: 'blur',
        validator: (val: string) => clusterNameSymbolRegx.test(val),
      },
      {
        message: t('集群重复'),
        trigger: 'blur',
        validator: (value: string) => clusterNameList.value.filter((item) => item === value).length < 2,
      },
      {
        message: t('该域名已被占用，请修改集群标识'),
        trigger: 'blur',
        validator: (val: string) => {
          const dbAppAbbr = props.appAbbr;
          if (!dbAppAbbr) {
            return true;
          }
          return checkDomainRepeat({
            cluster_type: ClusterTypes.REDIS_INSTANCE,
            db_app_abbr: dbAppAbbr,
            domains: [val],
          }).then((result) => {
            return !result[0].validate;
          });
        },
      },
    ],
    'masterHost.ip': [
      {
        message: t('必填项'),
        required: true,
        trigger: 'change',
      },
      {
        message: t('目标主库主机格式不正确'),
        validator: (value: string) => ipv4.test(value),
      },
      // {
      //   validator: (value: string) => masterHostIpList.value.filter(item => item === value).length < 2,
      //   message: t('目标主机重复'),
      // },
      {
        message: t('目标主库主机不存在'),
        validator: (value: string) =>
          getRedisMachineList({
            bk_city_name: props.cityInfo.city_name,
            bk_cloud_id: props.cloudId as number,
            cluster_type: ClusterTypes.REDIS_INSTANCE,
            instance_role: 'redis_master',
            ip: value,
          }).then((data) => {
            const redisMachineList = data.results;
            if (redisMachineList.length < 1) {
              return false;
            }
            return true;
          }),
      },
    ],
    'slaveHost.ip': [
      {
        message: t('必填项'),
        required: true,
        trigger: 'change',
      },
    ],
  };

  const columns = computed(() => {
    const baseColums: PrimaryTableCol[] = [
      {
        cell: (_, { rowIndex }) => String(rowIndex + 1),
        colKey: 'index',
        title: t('序号'),
        width: 60,
      },
      {
        cell: (_, { rowIndex }) => (
          <div class='cluster_name'>
            <div class='mr-4'>
              {/* ins. */}
              {getDomainPreview(domains.value[rowIndex]?.cluster_name).masterDomain.prefix}
            </div>
            <bk-form-item
              key={rowIndex}
              class={{
                'cell-item': true,
                'domain-address-item-empty': !domains.value[rowIndex]?.cluster_name,
              }}
              errorDisplayType='tooltips'
              label-width={0}
              property={`details.infos.${rowIndex}.cluster_name`}
              rules={rules.cluster_name}>
              <db-input
                v-bk-tooltips={{
                  content: t('仅支持小写字母、数字、连字符，同时会参与集群域名生成，创建后不可改'),
                  placement: 'top',
                  theme: 'light',
                  trigger: 'click',
                }}
                maxlength={63}
                model-value={domains.value[rowIndex]?.cluster_name}
                show-word-limit
                style='width: 200px'
                onChange={(value: string) => handleChangeCellValue(value, rowIndex, 'cluster_name')}>
                {{
                  suffix: () =>
                    domains.value[rowIndex]?.cluster_name && <span class='domain-address-placeholder ml-4'></span>,
                }}
              </db-input>
            </bk-form-item>
            {typeof props.portType === 'string' ? (
              <div class='ml-4'>
                {/* .{props.appAbbr}.db */}
                {getDomainPreview(domains.value[rowIndex]?.cluster_name).masterDomain.suffix}
                {props.isAppend ? '' : `#${props.portType === 'increment' ? props.port + rowIndex : props.port}`}
              </div>
            ) : (
              <div class='ml-4'>
                {/* .{props.appAbbr}.db */}
                {getDomainPreview(domains.value[rowIndex]?.cluster_name).masterDomain.suffix}
                {props.isAppend
                  ? ''
                  : `#${props.portType.length === tableData.value.length ? props.portType[rowIndex] : ''}`}
              </div>
            )}
          </div>
        ),
        colKey: 'cluster_name',
        minWidth: 300,
        title: () => (
          <div class='table-custom-label'>
            {t('主访问入口')}
            <span class='required-mark'>*</span>
            {tableData.value.length !== 0 && (
              <span v-bk-tooltips={t('批量编辑')}>
                <ClusterNameBatchEdit
                  appAbbr={props.appAbbr}
                  onChange={handleBatchClusterName}
                />
              </span>
            )}
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
        cell: (_, { rowIndex }) => (
          <bk-form-item
            key={rowIndex}
            class='cell-item'
            errorDisplayType='tooltips'
            label-width={0}
            property={`details.infos.${rowIndex}.databases`}>
            <db-input
              max={16}
              min={2}
              model-value={domains.value[rowIndex]?.databases}
              placeholder={t('范围 2～16')}
              type='number'
              onChange={(value: string) => handleChangeCellValue(value, rowIndex, 'databases')}
            />
          </bk-form-item>
        ),
        colKey: 'databases',
        title: () => (
          <div class='table-custom-label'>
            Databases
            <span class='required-mark'>*</span>
            {tableData.value.length !== 0 && (
              <span v-bk-tooltips={t('批量编辑')}>
                <DatabasesBatchEdit onChange={handleBatchDatabases} />
              </span>
            )}
          </div>
        ),
        width: 150,
      },
    ];
    const newColums: PrimaryTableCol[] = [
      {
        cell: () => props.maxMemory,
        colKey: 'maxmemory',
        title: 'Maxmemory',
        width: 200,
      },
    ];
    const appendColums: PrimaryTableCol[] = [
      {
        cell: (_, { rowIndex }) => (
          <bk-form-item
            key={rowIndex}
            class='cell-item master-ip-input-item'
            errorDisplayType='tooltips'
            label-width={0}
            property={`details.infos.${rowIndex}.masterHost.ip`}
            rules={rules['masterHost.ip']}>
            <db-input
              model-value={domains.value[rowIndex]?.masterHost.ip}
              placeholder={t('请输入或选择')}
              onChange={(value: string) => handleHostIpChange(value, rowIndex)}>
              {{
                suffix: () => (
                  <bk-button
                    class='mr-8'
                    text
                    onClick={() => handleInstancesSelectorShow(rowIndex)}>
                    <db-icon
                      v-bk-tooltips={t('选择主机')}
                      type='host-select'
                    />
                  </bk-button>
                ),
              }}
            </db-input>
          </bk-form-item>
        ),
        colKey: 'masterHost',
        title: () => (
          <div class='table-custom-label'>
            {t('待部署主库主机')}
            <span class='required-mark'>*</span>
            {tableData.value.length !== 0 && (
              <span v-bk-tooltips={t('批量编辑')}>
                <HostBatchEdit
                  cityName={props.cityInfo.city_name}
                  cloudId={props.cloudId}
                  onChange={handleBatchHost}
                />
              </span>
            )}
          </div>
        ),
        width: 220,
      },
      {
        cell: (_, { rowIndex }) => (
          <bk-form-item
            key={rowIndex}
            class='cell-item'
            errorDisplayType='tooltips'
            label-width={0}
            property={`details.infos.${rowIndex}.slaveHost.ip`}
            rules={rules['slaveHost.ip']}>
            <db-input
              model-value={domains.value[rowIndex]?.slaveHost.ip}
              placeholder={t('选择主库主机后自动生成')}
              readonly
            />
          </bk-form-item>
        ),
        colKey: 'slaveHost',
        title: t('待部署从库主机'),
        width: 220,
      },
    ];

    baseColums.push(...(props.isAppend ? appendColums : newColums));

    return baseColums;
  });

  const isShowInstanceSelector = ref(false);
  const instanceSelectorIndex = ref(-1);

  const selectedHostList = shallowRef({ RedisHost: [] } as InstanceSelectorValues<IValue>);

  const tabListConfig = computed(
    () =>
      ({
        RedisHost: [
          {
            tableConfig: {
              disabledRowConfig: {
                handler: (data: RedisMachineModel) => data.isUnvailable,
                tip: t('异常主机不可用'),
              },
              getTableList: (params: Record<string, any>) =>
                getRedisMachineList({
                  ...params,
                  bk_city_name: props.cityInfo.city_name,
                  bk_cloud_id: props.cloudId as number,
                  cluster_type: ClusterTypes.REDIS_INSTANCE,
                }),
            },
            topoConfig: {
              getTopoList: (params: ServiceParameters<typeof getRedisClusterList>) =>
                getRedisClusterList({
                  ...params,
                  region: props.cityInfo.city_code,
                }),
              totalCountFunc: (dataList: RedisModel[]) => {
                const ipSet = new Set<string>();
                dataList.forEach((dataItem) => dataItem.redis_master.forEach((masterItem) => ipSet.add(masterItem.ip)));
                return ipSet.size;
              },
            },
          },
          {
            manualConfig: {
              checkInstances: (params: Record<string, any>) =>
                getRedisMachineList({
                  ...params,
                  bk_city_name: props.cityInfo.city_name,
                  bk_cloud_id: props.cloudId as number,
                  cluster_type: ClusterTypes.REDIS_INSTANCE,
                }),
            },
            tableConfig: {
              disabledRowConfig: {
                handler: (data: RedisMachineModel) => data.isUnvailable,
                tip: t('异常主机不可用'),
              },
              getTableList: (params: Record<string, any>) =>
                getRedisMachineList({
                  ...params,
                  bk_city_name: props.cityInfo.city_name,
                  bk_cloud_id: props.cloudId as number,
                  cluster_type: ClusterTypes.REDIS_INSTANCE,
                }),
            },
          },
        ],
      }) as unknown as Record<'RedisHost', PanelListType>,
  );

  // 没有 appName 则不展示 table 数据
  const tableData = computed(() => {
    if (props.appAbbr) {
      return domains.value;
    }
    return [];
  });

  const clusterNameList = computed(() => tableData.value.map((item) => item.cluster_name));
  // const masterHostIpList = computed(() => tableData.value.map(item => item.masterHost.ip));

  const instanceSelectorKey = computed(() => `${props.cloudId}-${props.cityInfo.city_name}`);

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
    newDomains.map((item) => Object.assign(item, { databases: value }));
  };

  const handleBatchHost = (values: string[]) => {
    if (values.length !== 0) {
      const newDomains = domains.value;
      newDomains.forEach((item, index) => {
        if (values[index] !== undefined) {
          newDomains[index].masterHost.ip = values[index];
          emits('hostChange', `details.infos.${index}.masterHost.ip`, values[index], index);
        }
      });
      domains.value = newDomains;
    }
  };

  const handleChangeCellValue = (value: string, index: number, fieldName: string) => {
    const newDomains = _.cloneDeep(domains.value);
    Object.assign(newDomains[index], { [fieldName]: value });
    domains.value = newDomains;
  };

  const handleHostIpChange = (value: string, index: number) => {
    const newDomains = _.cloneDeep(domains.value);
    Object.assign(newDomains[index].masterHost, {
      ip: value,
    });
    domains.value = newDomains;
    emits('hostChange', `details.infos.${index}.masterHost.ip`, value, index);
  };

  const handleInstancesSelectorShow = (index: number) => {
    isShowInstanceSelector.value = true;
    instanceSelectorIndex.value = index;
  };

  const handleInstancesChange = (selectedValues: InstanceSelectorValues<IValue>) => {
    const { ip } = selectedValues.RedisHost[0];
    const newDomains = _.cloneDeep(domains.value);
    Object.assign(newDomains[instanceSelectorIndex.value].masterHost, {
      ip,
    });
    domains.value = newDomains;
    emits('hostChange', `details.infos.${instanceSelectorIndex.value}.masterHost.ip`, ip, instanceSelectorIndex.value);
    instanceSelectorIndex.value = -1;
  };

  const getDomainPreview = (clusterName: string) => {
    const strategy = getDomainStrategy(ClusterTypes.REDIS_INSTANCE);

    return strategy({
      clusterName,
      clusterType: ClusterTypes.REDIS_INSTANCE,
      dbAppAbbr: props.appAbbr,
    });
  };
</script>

<style lang="less">
  .domain-table {
    .t-table {
      .bk-form-content {
        margin-left: 0 !important;
      }

      tr:hover {
        .dbm-input,
        .dbm-input .dbm-input-text {
          background-color: #f5f7fa !important;
        }
      }
    }

    .table-custom-label {
      display: flex;
      align-items: center;
    }

    .cell-item {
      margin-bottom: 0;

      .bk-form-label {
        display: none;
      }

      .domain-address-placeholder {
        display: none;
      }

      &.is-error {
        .domain-address-placeholder {
          display: inline;
        }
      }
    }

    .domain-address-item-empty {
      .bk-form-error-tips {
        display: none;
      }
    }

    .domain-address-placeholder {
      min-width: 12px;
    }

    .required-mark {
      margin: 0 2px 0 6px;
      color: #ea3636;
    }

    .cluster_name {
      display: flex;
      align-items: center;
    }

    .bk-form-item {
      margin-bottom: 0;
    }

    .master-ip-input-item {
      .bk-form-error-tips {
        right: 26px;
      }
    }
  }
</style>
