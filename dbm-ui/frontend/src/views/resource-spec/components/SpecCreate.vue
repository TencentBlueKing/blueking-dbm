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
    ref="formWrapperRef"
    class="spec-create-form">
    <DbForm
      ref="formRef"
      form-type="vertical"
      :model="formdata">
      <BkFormItem
        :label="$t('规格名称')"
        property="spec_name"
        required>
        <BkInput
          v-model="formdata.spec_name"
          :maxlength="15"
          :placeholder="$t('请输入xx', [$t('虚拟机型名称')])"
          show-word-limit />
      </BkFormItem>
      <div class="machine-item">
        <div class="machine-item-label">
          {{ $t('后端存储机型') }}
        </div>
        <div class="machine-item-content">
          <SpecCPU
            v-model="formdata.cpu"
            :is-edit="isEdit" />
          <SpecMem
            v-model="formdata.mem"
            :is-edit="isEdit" />
          <SpecDevice
            v-model="formdata.device_class"
            :is-edit="isEdit" />
          <SpecStorage
            v-model="formdata.storage_spec"
            :is-edit="isEdit"
            :is-required="isRequired" />
        </div>
      </div>
      <BkFormItem
        v-if="hasInstance"
        :label="$t('每台主机实例数量')"
        property="instance_num"
        required>
        <BkInput
          v-model="formdata.instance_num"
          :min="1"
          type="number" />
      </BkFormItem>
      <BkFormItem :label="$t('描述')">
        <BkInput
          v-model="formdata.desc"
          :maxlength="100"
          :placeholder="$t('请输入xx', [$t('描述')])"
          show-word-limit
          type="textarea" />
      </BkFormItem>
    </DbForm>
  </div>
  <div
    ref="formFooterRef"
    class="spec-create-footer">
    <span
      v-bk-tooltips="{
        content: $t('请编辑配置'),
        disabled: isChange
      }"
      class="inline-block">
      <BkButton
        class="mr-8 w88"
        :disabled="!isChange"
        :loading="isLoading"
        theme="primary"
        @click="submit">
        {{ $t('提交') }}
      </BkButton>
    </span>
    <BkButton
      class="w88"
      :loading="isLoading"
      @click="cancel">
      {{ $t('取消') }}
    </BkButton>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import { createResourceSpec, updateResourceSpec } from '@services/resourceSpec';

  import { useStickyFooter  } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import SpecCPU from './spec-form-item/SpecCPU.vue';
  import SpecDevice from './spec-form-item/SpecDevice.vue';
  import SpecMem from './spec-form-item/SpecMem.vue';
  import SpecStorage from './spec-form-item/SpecStorage.vue';

  import { messageSuccess } from '@/utils';

  interface Emits {
    (e: 'cancel'): void,
    (e: 'successed'): void,
  }

  interface Props {
    clusterType: string,
    machineType: string,
    isEdit: boolean,
    hasInstance: boolean,
    data: ResourceSpecModel | null
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const initFormdata = () => {
    if (props.data) {
      const baseData = { ...props.data };
      if (baseData.device_class.length === 0) {
        baseData.device_class = [''];
      }
      return baseData;
    }

    return {
      cpu: {
        max: '' as string | number,
        min: '' as string | number,
      },
      mem: {
        max: '' as string | number,
        min: '' as string | number,
      },
      storage_spec: [
        {
          mount_point: '',
          size: '' as string | number,
          type: '',
        },
      ],
      device_class: [] as string[],
      desc: '',
      spec_cluster_type: props.clusterType,
      spec_machine_type: props.machineType,
      spec_name: '',
      instance_num: 1,
    };
  };

  const { t } = useI18n();

  const formRef = ref();
  const formWrapperRef = ref<HTMLDivElement>();
  const formFooterRef = ref<HTMLDivElement>();
  const formdata = ref(initFormdata());
  const isLoading = ref(false);
  const initFormdataStringify = JSON.stringify(formdata.value);
  const isChange = computed(() => JSON.stringify(formdata.value) !== initFormdataStringify);
  const notRequiredStorageList = [
    `${ClusterTypes.TWEMPROXY_REDIS_INSTANCE}_twemproxy`,
    `${ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE}_twemproxy`,
    `${ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER}_predixy`,
    `${ClusterTypes.ES}_es_client`,
    `${ClusterTypes.PULSAE}_pulsar_broker`,
  ];
  const isRequired = computed(() => !notRequiredStorageList.includes(`${props.clusterType}_${props.machineType}`));

  useStickyFooter(formWrapperRef, formFooterRef);

  const submit = () => {
    isLoading.value = true;
    formRef.value.validate()
      .then(() => {
        const params = {
          ...formdata.value,
          device_class: formdata.value.device_class.filter(item => item),
          storage_spec: formdata.value.storage_spec.filter(item => item.mount_point && item.size && item.type),
        };
        if (props.isEdit) {
          updateResourceSpec((formdata.value as ResourceSpecModel).spec_id, params)
            .then(() => {
              messageSuccess(t('编辑成功'));
              emits('successed');
              window.changeConfirm = false;
            })
            .finally(() => {
              isLoading.value = false;
            });
          return;
        }

        if (!props.hasInstance) {
          delete params.instance_num;
        }

        createResourceSpec(params)
          .then(() => {
            messageSuccess(t('新建成功'));
            emits('successed');
            window.changeConfirm = false;
          })
          .finally(() => {
            isLoading.value = false;
          });
      })
      .catch(() => {
        isLoading.value = false;
      });
  };

  const cancel = () => {
    emits('cancel');
  };
</script>

<style lang="less" scoped>
  .spec-create-form {
    padding: 28px 40px 21px;

    :deep(.bk-form-label) {
      font-weight: bold;
    }

    .machine-item {
      &-label {
        position: relative;
        margin-bottom: 8px;
        font-size: 12px;
        font-weight: bold;
        line-height: 20px;

        &::after {
          position: absolute;
          width: 14px;
          font-weight: normal;
          color: @danger-color;
          text-align: center;
          content: "*";
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
          content: "";
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
          content: "";
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
          content: "AND";
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
            content: "";
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
            content: "";
          }
        }
      }
    }
  }

  .spec-create-footer {
    padding: 11px 40px;
  }
</style>
