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
      class="domain-address"
      :columns="columns"
      :data="tableData"
      :empty-text="t('请选择业务和DB模块名')" />
  </div>
</template>

<script setup lang="tsx">
  import { Form } from 'bkui-vue';
  import type { Column } from 'bkui-vue/lib/table/props';
  import { useI18n } from 'vue-i18n';

  import { checkDomainRepeat } from '@services/source/ticket.tsx';

  import { ClusterTypes } from '@common/const/clusterTypes.ts';
  import { clusterNameFormatRegx, clusterNameSymbolRegx } from '@common/regex';

  import { getDomainStrategy } from '@views/db-manage/utils/getDomainPreview.ts';

  import ClusterIdBatchEdit from './ClusterIdBatchEdit.vue';
  import ClusterNameBatchEdit from './ClusterNameBatchEdit.vue';

  type FormItem = typeof Form.FormItem;

  interface Domain {
    [key: string]: string;
    domain: string;
    name: string;
    set_id: string;
  }

  interface Props {
    appAbbr: string;
    nodesNumber: number;
  }

  const props = defineProps<Props>();
  const domains = defineModel<Array<Domain>>('domains', {
    default: () => [],
  });

  const { t } = useI18n();

  const rules = {
    set_id: [
      {
        message: '',
        required: true,
        trigger: 'blur',
        validator: (val: string) => !!val,
      },
      // {
      //   message: t('最大长度为m', { m: 63 }),
      //   trigger: 'blur',
      //   validator: (val: string) => val.length <= 63,
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
        message: t('集群ID重复'),
        trigger: 'blur',
        validator: (val: string) => clusterIdKeys.value.filter((item) => item === val).length < 2,
      },
      {
        message: t('该域名已被占用，请修改集群标识'),
        trigger: 'blur',
        validator: (val: string) => {
          if (!props.appAbbr) {
            return true;
          }
          return checkDomainRepeat({
            cluster_type: ClusterTypes.MONGO_REPLICA_SET,
            db_app_abbr: props.appAbbr,
            domains: [val],
          }).then((result) => {
            return !result[0].validate;
          });
        },
      },
    ],
    // name: [
    //   {
    //     required: true,
    //     message: t('必填项'),
    //     trigger: 'change',
    //   },
    //   {
    //     message: t('最大长度为m', { m: 63 }),
    //     trigger: 'blur',
    //     validator: (val: string) => val.length <= 63,
    //   },
    //   {
    //     message: t('集群ID重复'),
    //     trigger: 'blur',
    //     validator: (val: string) => clusterNameKeys.value.filter(item => item === val).length < 2,
    //   },
    // ],
  };

  const columns: Column[] = [
    {
      label: t('序号'),
      render: ({ index }: { index: number }) => index + 1,
      // type: 'index',
      width: 80,
    },
    {
      field: 'domain',
      label: t('主域名'),
      render: ({ data }: { data: Domain }) => getDomainDisplay(data.set_id),
      width: 200,
    },
    {
      field: 'set_id',
      label: () => (
        <div class='table-custom-label'>
          {t('集群ID')}
          {tableData.value.length !== 0 && (
            <span v-bk-tooltips={t('批量录入')}>
              <ClusterIdBatchEdit onChange={(value) => handleBatchEdit(value, 'set_id')} />
            </span>
          )}
          <span class='required-mark ml-4'>*</span>
        </div>
      ),
      minWidth: 300,
      render: ({ index }: { index: number }) => (
        <bk-form-item
          key={index}
          ref={(value: FormItem) => setSetIdRef(value)}
          class={{
            'cell-item': true,
            'domain-address-item-empty': !domains.value[index]?.set_id,
          }}
          errorDisplayType='tooltips'
          label-width={0}
          property={`details.replica_sets.${index}.set_id`}
          rules={rules.set_id}>
          <db-input
            v-bk-tooltips={{
              content: t('仅支持小写字母、数字、连字符，同时会参与集群域名生成，创建后不可改'),
              placement: 'top',
              theme: 'light',
              trigger: 'click',
            }}
            maxlength={63}
            model-value={domains.value[index]?.set_id}
            placeholder={t('请输入')}
            show-word-limit
            onInput={(value: string) => handleChangeCellValue(value, index, 'set_id')}>
            {{
              suffix: () => domains.value[index]?.set_id && <span class='domain-address-placeholder ml-4'></span>,
            }}
          </db-input>
        </bk-form-item>
      ),
    },
    {
      field: 'name',
      label: () => (
        <div class='table-custom-label'>
          {t('集群名称')}
          {tableData.value.length !== 0 && (
            <span v-bk-tooltips={t('批量录入')}>
              <ClusterNameBatchEdit onChange={(value) => handleBatchEdit(value, 'name')} />
            </span>
          )}
        </div>
      ),
      minWidth: 300,
      render: ({ index }: { index: number }) => (
        <bk-form-item
          key={index}
          ref={(value: FormItem) => setNameRef(value)}
          class='cell-item'
          errorDisplayType='tooltips'
          label-width={0}
          property={`details.replica_sets.${index}.name`}>
          <db-input
            model-value={domains.value[index]?.name}
            placeholder={t('请输入')}
            onInput={(value: string) => handleChangeCellValue(value, index, 'name')}
          />
        </bk-form-item>
      ),
    },
  ];

  const clusterIdRefs: FormItem[] = [];
  const clusterNameRefs: FormItem[] = [];

  // 没有 appName 则不展示 table 数据
  const tableData = computed(() => {
    if (props.appAbbr) {
      return domains.value;
    }
    return [];
  });
  const clusterIdKeys = computed(() => tableData.value.map((item) => item.set_id));
  // const clusterNameKeys = computed(() => tableData.value.map(item => item.name));

  watch(
    () => props.nodesNumber,
    () => {
      clusterIdRefs.splice(0, clusterIdRefs.length - 1);
      clusterNameRefs.splice(0, clusterNameRefs.length - 1);
    },
  );

  const setSetIdRef = (el: FormItem) => {
    if (el) {
      clusterIdRefs.push(el);
    }
  };

  const setNameRef = (el: FormItem) => {
    if (el) {
      clusterNameRefs.push(el);
    }
  };

  const generateDomian = (setId: string) => `m1.${setId}.${props.appAbbr}.db`;

  const handleBatchEdit = (values: string[], fieldName: keyof Domain) => {
    if (values.length !== 0) {
      const newDomains = domains.value;
      newDomains.forEach((item, index) => {
        if (values[index] !== undefined) {
          newDomains[index][fieldName] = values[index];

          // 主域名根据集群ID自动生成
          if (fieldName === 'set_id') {
            newDomains[index].domain = generateDomian(values[index]);
          }
        }
      });
      domains.value = newDomains;
      // 校验集群ID信息
      nextTick(() => {
        if (fieldName === 'set_id') {
          clusterIdRefs.forEach((item) => item?.validate?.());
        } else {
          clusterNameRefs.forEach((item) => item?.validate?.());
        }
      });
    }
  };

  const handleChangeCellValue = (value: string, index: number, fieldName: keyof Domain) => {
    const newDomains = domains.value;
    newDomains[index][fieldName] = value;

    // 主域名根据集群ID自动生成
    if (fieldName === 'set_id') {
      newDomains[index].domain = generateDomian(value);
    }

    domains.value = newDomains;
  };

  const getDomainDisplay = (domain: string) => {
    const strategy = getDomainStrategy(ClusterTypes.MONGO_REPLICA_SET);
    const domainInfo = strategy({
      clusterName: domain,
      dbAppAbbr: props.appAbbr,
      moduleName: '',
    });

    return `${domainInfo.masterDomain.prefix}${domain || '{' + t('集群标识') + '}'}${domainInfo.masterDomain.suffix}`;
  };
</script>

<style lang="less">
  .domain-table {
    .bk-table {
      .bk-form-content {
        margin-left: 0 !important;
      }
    }

    .table-custom-label {
      display: flex;
      align-items: center;

      .required-mark {
        color: #ea3636;
      }
    }

    .domain-address {
      // display: flex;
      // align-items: center;

      // > span {
      //   flex-shrink: 0;
      // }

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
    }
  }
</style>
