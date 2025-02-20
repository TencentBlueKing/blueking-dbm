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
  <div class="spec-create-form">
    <DbForm
      ref="formRef"
      form-type="vertical"
      :model="formdata">
      <BkFormItem
        ref="nameInputRef"
        :label="t('规格名称')"
        property="spec_name"
        required
        :rules="nameRules">
        <BkInput
          v-model="formdata.spec_name"
          :maxlength="128"
          :placeholder="t('请输入')"
          show-word-limit
          @input="handleInputName" />
      </BkFormItem>
      <div class="machine-item">
        <div class="machine-item-label">
          {{ machineTypeLabel }}
        </div>
        <div class="machine-item-content">
          <SpecDeviceOrCpuMem
            ref="specDeviceOrCpuMemRef"
            v-model:cpu="formdata.cpu"
            v-model:device-class="formdata.device_class"
            v-model:mem="formdata.mem"
            :is-edit="isEdit" />
          <SpecStorage
            ref="specStorageRef"
            :data="formdata.storage_spec"
            :db-type="dbType"
            :is-edit="isEdit"
            :is-required="isRequired"
            @table-value-change="handleTableValueChange" />
        </div>
      </div>
      <BkFormItem
        v-if="hasInstance"
        :label="t('每台主机实例数量')"
        property="instance_num"
        required>
        <BkInput
          v-model="formdata.instance_num"
          :min="1"
          type="number" />
      </BkFormItem>
      <SpecQps
        v-if="hasQPS && formdata.qps"
        v-model="formdata.qps"
        :is-edit="isEdit" />
      <BkFormItem :label="t('描述')">
        <BkInput
          v-model="formdata.desc"
          :maxlength="100"
          :placeholder="t('请输入xx', [t('描述')])"
          show-word-limit
          type="textarea" />
      </BkFormItem>
      <BkFormItem :label="t('是否启用')">
        <BkPopConfirm
          :confirm-text="formdata.enable ? t('停用') : t('启用')"
          :content="
            formdata.enable
              ? t('停用后，在资源规格选择时，将不可见，且不可使用')
              : t('启用后，在资源规格选择时，将开放选择')
          "
          :is-show="isShowSwitchTip"
          placement="bottom"
          :title="formdata.enable ? t('确认停用该规格？') : t('确认启用该规格？')"
          trigger="manual"
          width="308"
          @cancel="handleCancelSwitch"
          @confirm="handleConfirmSwitch">
          <BkSwitcher
            v-model="formdata.enable"
            size="small"
            theme="primary"
            @change="handleChangeSwitch" />
        </BkPopConfirm>
      </BkFormItem>
    </DbForm>
  </div>
  <div class="spec-create-footer">
    <span
      v-bk-tooltips="{
        content: t('请编辑配置'),
        disabled: isChange,
      }"
      class="inline-block">
      <BkButton
        class="mr-8 w-88"
        :disabled="!isChange"
        :loading="isLoading"
        theme="primary"
        @click="submit">
        {{ t('提交') }}
      </BkButton>
    </span>
    <BkButton
      class="w-88"
      :loading="isLoading"
      @click="cancel">
      {{ t('取消') }}
    </BkButton>
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import type ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import { createResourceSpec, updateResourceSpec, verifyDuplicatedSpecName } from '@services/source/dbresourceSpec';

  import { ClusterTypes, DBTypes } from '@common/const';

  import { messageSuccess } from '@/utils';

  import { useHasQPS } from '../hooks/useHasQPS';

  import SpecDeviceOrCpuMem from './spec-form-item/spec-device-or-cpu-mem/Index.vue';
  import SpecStorage from './spec-form-item/spec-storage/Index.vue';
  import SpecQps from './spec-form-item/SpecQPS.vue';

  interface Emits {
    (e: 'cancel'): void;
    (e: 'successed'): void;
  }

  interface Data extends Omit<ResourceSpecModel, 'device_class'> {
    device_class: string[];
  }

  interface Props {
    data: Data | null;
    dbType: string;
    hasInstance: boolean;
    isEdit: boolean;
    machineType: string;
    machineTypeLabel: string;
    mode: string;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const specDeviceOrCpuMemRef = ref<InstanceType<typeof SpecDeviceOrCpuMem>>();
  const specStorageRef = ref<InstanceType<typeof SpecStorage>>();

  const notRequiredStorageList = [
    `${DBTypes.MYSQL}_proxy`,
    `${DBTypes.REDIS}_${ClusterTypes.TWEMPROXY_REDIS_INSTANCE}`,
    `${DBTypes.REDIS}_${ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE}`,
    `${DBTypes.REDIS}_${ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER}`,
    `${DBTypes.ES}_es_client`,
    `${DBTypes.PULSAR}_pulsar_broker`,
    `${DBTypes.TENDBCLUSTER}_proxy`,
    `${DBTypes.SQLSERVER}_sqlserver`,
  ];

  const isRequired = !notRequiredStorageList.includes(`${props.dbType}_${props.machineType}`);

  const isSqlserver = computed(() => props.dbType === DBTypes.SQLSERVER);

  const initFormdata = () => {
    if (props.data) {
      const data = _.cloneDeep(props.data);
      return data;
    }

    const genStorageSpec = () => [
      {
        mount_point: isRequired ? '/data' : '',
        size: '' as string | number,
        type: '',
      },
    ];

    const genSystemDriveStorageSpec = () => [
      {
        isSystemDrive: true,
        mount_point: 'C:\\',
        size: '' as string | number,
        type: '',
      },
      {
        isSystemDrive: true,
        mount_point: 'D:\\',
        size: '' as string | number,
        type: '',
      },
    ];

    return {
      cpu: {
        max: '' as string | number,
        min: '' as string | number,
      },
      desc: '',
      device_class: [],
      enable: true,
      instance_num: 1,
      mem: {
        max: '' as string | number,
        min: '' as string | number,
      },
      qps: {
        max: '',
        min: '',
      },
      spec_cluster_type: props.dbType,
      spec_id: undefined,
      spec_machine_type: props.machineType,
      spec_name: '',
      storage_spec: isSqlserver.value ? genSystemDriveStorageSpec() : genStorageSpec(),
    };
  };

  const { t } = useI18n();
  const { hasQPS } = useHasQPS(props);

  const formRef = ref();
  const nameInputRef = ref();
  const formdata = ref(initFormdata());
  const isLoading = ref(false);
  const isCustomInput = ref(false);
  const isShowSwitchTip = ref(false);
  const isTableValueChange = ref(false);
  const initFormdataStringify = JSON.stringify(formdata.value);

  const isChange = computed(() => JSON.stringify(formdata.value) !== initFormdataStringify || isTableValueChange.value);

  const nameRules = computed(() => [
    {
      message: t('规格名称不能为空'),
      required: true,
      trigger: 'blur',
      validator: (value: string) => !!value,
    },
    {
      message: t('规格名称已存在_请修改规格'),
      trigger: 'blur',
      validator: (value: string) =>
        verifyDuplicatedSpecName({
          spec_cluster_type: props.dbType,
          spec_id: props.mode === 'edit' ? formdata.value.spec_id : undefined,
          spec_machine_type: props.machineType,
          spec_name: value,
        }).then((exists) => !exists),
    },
  ]);

  watch(
    [() => formdata.value.cpu, () => formdata.value.mem, () => formdata.value.storage_spec, () => formdata.value.qps],
    () => {
      if (props.mode === 'create' && isCustomInput.value === false) {
        formdata.value.spec_name = getName();
        nameInputRef.value?.clearValidate();
      }
    },
    { deep: true },
  );

  const handleTableValueChange = () => {
    isTableValueChange.value = true;
  };

  const handleCancelSwitch = () => {
    isShowSwitchTip.value = false;
  };

  const handleChangeSwitch = () => {
    isShowSwitchTip.value = true;
    formdata.value.enable = !formdata.value.enable;
  };

  const handleConfirmSwitch = () => {
    formdata.value.enable = !formdata.value.enable;
    handleCancelSwitch();
  };

  const getName = () => {
    const { cpu, mem, qps, storage_spec: StorageSpec } = formdata.value;
    const displayList = [
      {
        unit: t('核'),
        value: cpu.min,
      },
      {
        unit: 'G',
        value: mem.min,
      },
      {
        unit: 'G',
        value: Math.min(...StorageSpec.map((item) => Number(item.size))),
      },
      {
        unit: '/s',
        value: qps?.min ?? 0,
      },
    ];
    return displayList
      .filter((item) => item.value)
      .map((item) => item.value + item.unit)
      .join('_');
  };

  const handleInputName = () => {
    isCustomInput.value = true;
  };

  const submit = async () => {
    isLoading.value = true;
    try {
      await formRef.value.validate();
      const storageSpec = await specStorageRef.value!.getValue();
      const params = Object.assign(_.cloneDeep(formdata.value), {
        device_class: formdata.value.device_class[0] === '-1' ? [] : formdata.value.device_class,
        spec_id: (formdata.value as ResourceSpecModel).spec_id,
        storage_spec: storageSpec,
      });
      const type = specDeviceOrCpuMemRef.value!.getCurrentType();
      if (type === 'device_class') {
        const deviceClassCpuMem = specDeviceOrCpuMemRef.value!.getDeviceClassCpuMem();
        Object.assign(params, deviceClassCpuMem);
      } else {
        params.device_class = [];
      }

      if (props.mode === 'edit') {
        updateResourceSpec(params).then(() => {
          messageSuccess(t('编辑成功'));
          emits('successed');
          window.changeConfirm = false;
        });
        return;
      }

      if (!props.hasInstance) {
        delete params.instance_num;
      }

      if (hasQPS) {
        params.qps = {
          max: Number(params.qps?.max),
          min: Number(params.qps?.min),
        };
      } else {
        delete params.qps;
      }

      createResourceSpec(params).then(() => {
        messageSuccess(t('新建成功'));
        emits('successed');
        window.changeConfirm = false;
      });
    } finally {
      isLoading.value = false;
    }
  };

  const cancel = () => {
    emits('cancel');
  };
</script>

<style lang="less" scoped>
  .spec-create-form {
    max-height: calc(100vh - 105px);
    padding: 28px 40px 21px;
    overflow-y: auto;

    :deep(.bk-form-label) {
      font-weight: bold;
      color: @title-color;
    }

    .machine-item {
      &-label {
        position: relative;
        margin-bottom: 8px;
        font-size: 12px;
        font-weight: bold;
        line-height: 20px;
        color: @title-color;

        &::after {
          position: absolute;
          width: 14px;
          font-weight: normal;
          color: @danger-color;
          text-align: center;
          content: '*';
        }
      }

      &-content {
        position: relative;

        &::before {
          position: absolute;
          top: 0;
          left: 20px;
          width: 1px;
          height: 100%;
          background-color: #dcdee5;
          content: '';
        }
      }

      .spec-form-item {
        position: relative;
        margin-bottom: 16px;
        margin-left: 56px;

        &::before {
          position: absolute;
          top: 50%;
          left: -35px;
          width: 35px;
          height: 1px;
          line-height: 22px;
          background-color: #dcdee5;
          content: '';
        }

        &::after {
          position: absolute;
          bottom: -18px;
          left: -56px;
          width: 42px;
          line-height: 22px;
          color: @primary-color;
          text-align: center;
          background-color: #e1ecff;
          content: 'AND';
        }

        &:first-child {
          &::before {
            top: 0;
            left: -36px;
            width: 36px;
            height: 50%;
            background-color: white;
            border-bottom: 1px solid #dcdee5;
            border-left: 1px solid white;
            content: '';
          }
        }

        &:last-child {
          &::after {
            display: none;
          }

          &::before {
            top: 50%;
            left: -36px;
            width: 36px;
            height: 50%;
            background-color: white;
            border-top: 1px solid #dcdee5;
            border-left: 1px solid white;
            content: '';
          }
        }
      }
    }
  }

  .spec-create-footer {
    padding: 11px 40px;
  }
</style>
