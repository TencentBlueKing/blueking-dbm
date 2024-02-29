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
  <BkSideslider
    :before-close="handleClose"
    :is-show="isShow"
    :width="1100"
    @closed="handleClose">
    <template #header>
      <div class="header-main">
        {{ t('新建订阅') }}
      </div>
    </template>
    <div class="dumper-config-edit-box">
      <BkRadioGroup
        v-if="showTabPanel"
        v-model="createType"
        class="mb-24"
        type="card">
        <BkRadioButton
          v-for="(item, index) in createTypeList"
          :key="index"
          :label="item.value"
          @change="handleChangeCreateType">
          {{ item.label }}
        </BkRadioButton>
      </BkRadioGroup>
      <BkForm
        ref="formRef"
        class="edit-form"
        form-type="vertical"
        :model="formModel"
        :rules="formRules">
        <BkFormItem
          :label="t('名称')"
          property="name"
          required>
          <BkInput
            v-if="!isUseExistedSubscribe"
            v-model="formModel.name" />
          <BkSelect
            v-else
            v-model="formModel.name"
            :clearable="false"
            filterable
            :input-search="false"
            @change="(id: number) => handleSelectSubscribeName(id)">
            <BkOption
              v-for="(item, index) in subscribeNameList"
              :key="index"
              :label="item.label"
              :value="item.value" />
            <template #extension>
              <BkButton
                class="create-module"
                text
                @click="handleGoDumper">
                <i class="db-icon-plus-circle" />
                {{ $t('新建订阅规则') }}
              </BkButton>
            </template>
          </BkSelect>
        </BkFormItem>
        <BkFormItem
          v-if="!isUseExistedSubscribe"
          :label="t('订阅库表')"
          required>
          <div
            class="control-box"
            style="padding-bottom: 14px">
            <SubscribeDbTable ref="subscribeDbTableRef" />
          </div>
        </BkFormItem>
        <BkFormItem
          v-else
          :label="t('订阅库表')">
          <BkTable
            class="subscribe-table"
            :columns="subscribeColumns"
            :data="subscribeTableData" />
        </BkFormItem>
        <BkFormItem
          :label="t('数据源与接收端配置')"
          property="clusterList"
          required>
          <ReceiverData
            ref="receiverDataRef"
            :selected-cluster-list="selectedClusters" />
        </BkFormItem>
        <BkFormItem
          :label="t('Dumper部署位置')"
          required>
          <BkRadio
            v-model="deployPlace"
            class="deploy-place-radio"
            disabled
            label="master">
            {{ t('集群Master所在主机') }}
          </BkRadio>
        </BkFormItem>
        <BkFormItem
          :label="t('数据同步方式')"
          required>
          <BkRadioGroup v-model="syncType">
            <BkRadio label="full_sync">
              {{ t('全量同步') }}
            </BkRadio>
            <BkRadio label="incr_sync">
              {{ t('增量同步') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
      </BkForm>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        :disabled="isReadonlyPage"
        :loading="isSubmitting"
        theme="primary"
        @click="handleConfirm">
        {{ t('提交') }}
      </BkButton>
      <BkButton @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import {
    listDumperConfig,
    verifyDuplicateName,
  } from '@services/source/dumper';
  import { createTicket } from '@services/source/ticket';

  import {
    useBeforeClose,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import ReceiverData from './components/receiver-data/Index.vue';
  import SubscribeDbTable from './components/subscribe-db-table/Index.vue';

  interface Props {
    showTabPanel?: boolean,
    pageStatus?: string,
    selectedClusters?: TendbhaModel[],
  }

  interface Emits {
    (e: 'success'): void,
    (e: 'cancel'): void,
  }

  type DumperConfig = ServiceReturnType<typeof listDumperConfig>['results'][number]

  const props = withDefaults(defineProps<Props>(), {
    showTabPanel: false,
    pageStatus: 'edit',
    selectedClusters: () => ([]),
  });
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>();

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();
  const router = useRouter();

  const formRef = ref();
  const subscribeDbTableRef = ref();
  const receiverDataRef = ref();
  const deployPlace = ref('master');
  const syncType = ref('full_sync');
  const createType = ref('new');
  const isSubmitting = ref(false);
  const subscribeNameList = ref<SelectItem<number>[]>([]);
  const subscribeTableData = ref<DumperConfig['repl_tables']>([]);

  const formModel = reactive<{
    name: string | number,
    clusterList: string[],
  }>({
    name: '',
    clusterList: [''],
  });

  const isUseExistedSubscribe = computed(() => createType.value === 'old');
  const isReadonlyPage = computed(() => props.pageStatus === 'read');

  const createTypeList = [
    {
      value: 'new',
      label: t('新建订阅'),
    },
    {
      value: 'old',
      label: t('使用已有订阅'),
    },
  ];

  const subscribeColumns = [
    {
      label: t('DB 名'),
      field: 'db_name',
      width: 300,
    },
    {
      label: t('表名'),
      field: 'table_names',
      minWidth: 100,
      render: ({ data }: {data: { table_names: string[] }}) => (
        <div class="table-names-box">
          {
            data.table_names.map((item, index) => <div key={index} class="name-item">{ item }</div>)
          }
        </div>
      ),
    },
  ];

  const formRules = {
    name: [
      {
        validator: (value: string) => Boolean(value),
        message: t('订阅名称不能为空'),
        trigger: 'blur',
      },
      {
        validator: (value: string) => {
          if (value.length > 128) {
            return false;
          }
          return true;
        },
        message: t('不能超过n个字符', { n: 128 }),
        trigger: 'blur',
      },
      {
        validator: async (name: string) => {
          if (isUseExistedSubscribe.value) {
            return true;
          }
          const isDuplicate = await verifyDuplicateName({ name });
          return !isDuplicate;
        },
        message: t('订阅名称重复'),
        trigger: 'blur',
      },
    ],
    clusterList: [
      {
        validator: () => {
          const list = receiverDataRef.value.getTableValue();
          return list.length;
        },
        message: t('不能为空'),
        trigger: 'change',
      },
    ],
  };

  const replTableMap: Record<string, DumperConfig['repl_tables']> = {};

  watch(() => formModel.name, (name) => {
    if (name) {
      window.changeConfirm = true;
    }
  }, {
    immediate: true,
  });

  useRequest(listDumperConfig, {
    defaultParams: [
      {
        offset: 0,
        limit: -1,
      },
    ],
    onSuccess: (data) => {
      const list: SelectItem<number>[] = [];
      data.results.forEach((item) => {
        list.push({
          label: item.name,
          value: item.id,
        });
        replTableMap[item.id] = item.repl_tables;
      });
      subscribeNameList.value = list;
    },
  });

  const initFormData = () => {
    formModel.name = '';
  };

  const handleGoDumper = () => {
    router.push({
      name: 'DumperDataSubscription',
    });
  };

  const handleChangeCreateType = () => {
    initFormData();
  };

  const handleSelectSubscribeName = (id: number) => {
    subscribeTableData.value = replTableMap[id];
  };

  // 点击确定
  const handleConfirm = async () => {
    await formRef.value.validate();
    const replTables = isUseExistedSubscribe.value
      ? replTableMap[formModel.name] : await subscribeDbTableRef.value.getValue();
    const infos = await receiverDataRef.value.getValue();
    const params = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.TBINLOGDUMPER_INSTALL,
      remark: '',
      details: {
        name: isUseExistedSubscribe.value
          ? subscribeNameList.value.find(item => item.value === formModel.name)?.label : formModel.name,
        add_type: syncType.value,
        repl_tables: replTables,
        infos,
      },

    };
    isSubmitting.value = true;
    try {
      const data = await createTicket(params);
      if (data && data.id) {
        ticketMessage(data.id);
        initFormData();
        emits('success');
        isShow.value = false;
      }
      window.changeConfirm = false;
    } finally {
      isSubmitting.value = false;
    }
  };

  async function handleClose() {
    const result = await handleBeforeClose();
    if (!result) return;
    window.changeConfirm = false;
    initFormData();
    createType.value = 'new';
    emits('cancel');
    isShow.value = false;
  }
</script>

<style lang="less" scoped>
  .header-main {
    display: flex;
    width: 100%;
    overflow: hidden;
    align-items: center;

    .name {
      width: auto;
      max-width: 720px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .dumper-config-edit-box {
    display: flex;
    width: 100%;
    padding: 24px 40px;
    flex-direction: column;

    .control-box {
      padding: 24px 24px 0;
      background-color: #f5f7fa;
      border-radius: 2px;
    }

    .subscribe-table {
      :deep(.table-names-box) {
        display: flex;
        width: 100%;
        flex-wrap: wrap;
        padding-top: 10px;
        padding-bottom: 2px;

        .name-item {
          height: 22px;
          padding: 0 8px;
          margin-right: 4px;
          margin-bottom: 8px;
          line-height: 22px;
          color: #63656e;
          background: #f0f1f5;
          border-radius: 2px;
        }
      }

      :deep(th) {
        .head-text {
          color: #313238;
        }
      }
    }

    .edit-form {
      // :deep(.bk-form-label) {
      //   font-weight: 700;
      // }

      :deep(.deploy-place-radio) {
        .bk-radio-label {
          color: #63656e;
        }
      }
    }

    .item-title {
      margin-bottom: 6px;
      font-weight: normal;
      color: #63656e;
    }

    .name-tip {
      height: 20px;
      margin-bottom: 6px;
      font-size: 12px;
      color: #ea3636;
    }

    .check-rules {
      display: flex;
      flex-direction: column;
      gap: 16px;

      .title-icon {
        display: flex;
        width: 24px;
        height: 24px;
        font-size: 16px;
        color: #3a84ff;
        background-color: #f0f5ff;
        border: none;
        border-radius: 50%;
        justify-content: center;
        align-items: center;
      }

      .icon-warn {
        color: #ff9c01;
        background-color: #fff3e1;
      }

      .icon-dander {
        color: #ea3636;
        background-color: #fee;
      }
    }

    .notify-select {
      :deep(.alarm-icon) {
        font-size: 18px;
        color: #979ba5;
      }

      :deep(.notify-tag-box) {
        display: flex;
        height: 22px;
        padding: 0 6px;
        background: #f0f1f5;
        border-radius: 2px;
        align-items: center;

        .close-icon {
          font-size: 14px;
          color: #c4c6cc;
        }
      }
    }
  }

  .create-module {
    display: block;
    width: 100%;
    padding: 0 8px;
    text-align: left;

    .db-icon-plus-circle {
      margin-right: 4px;
    }

    &:hover:not(.is-disabled) {
      color: @primary-color;
    }
  }
</style>
