<template>
  <BkSideslider
    v-model:is-show="isShow"
    background-color="#FFFFFF"
    class="kafka-topic-sideslider"
    quick-close
    :width="960">
    <template #header>
      {{ t('KafKa Topic 均衡') }}
      <div class="kafka-topic-header">
        {{ data?.cluster_name || '' }}
      </div>
    </template>
    <div class="kafka-topic-main">
      <BkForm
        ref="form"
        form-type="vertical"
        :model="formData">
        <div class="kafka-topic-group">
          <BkFormItem
            class="kafka-topic-group-item"
            field="topics"
            label="Topic"
            required>
            <div style="display: none">
              <div
                ref="pop"
                style="font-size: 12px; line-height: 24px; color: #63656e">
                <div class="topics-tip">
                  <div>
                    <div class="circle-dot"></div>
                    <span>{{ t('支持 *通配符') }}</span>
                  </div>
                  <div>
                    <div class="circle-dot"></div>
                    <span>{{ t('可同时输入多个对象，使用换行、空格或；，竖线分隔，按 Enter或失焦完成内容输入') }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div
              ref="root"
              @click="handleShowTips">
              <BkTagInput
                v-model="formData.topics"
                allow-create
                collapse-tags
                has-delete-icon />
            </div>
          </BkFormItem>
          <BkFormItem
            class="kafka-topic-group-item"
            field="throttle_rate"
            :label="t('速率')"
            required>
            <div class="flex-center">
              <BkInput
                v-model="formData.throttle_rate"
                type="number">
              </BkInput>
              <span class="ml-8">byte/s</span>
            </div>
          </BkFormItem>
        </div>
        <BkFormItem
          field="instance_list"
          :label="t('Broker 列表')">
          <template #label>
            <div class="instance-list-form-item">
              <div class="flex-center">
                <div class="title-spot instance-list-label">{{ t('Broker 列表') }}<span class="required" /></div>
                <div class="ml-22 kafka-topic-header instance-list-sub-title">
                  <I18nT
                    v-if="checkNum"
                    keypath="已选数量：n"
                    tag="p">
                    <strong>{{ checkNum }}</strong>
                  </I18nT>
                  <span v-else>{{ t('请选择 Broker 实例') }}</span>
                </div>
              </div>
              <div class="flex-center">
                <div
                  v-bk-tooltips="{
                    content: t('未勾选 Broker 实例'),
                    disabled: !!checkNum,
                    theme: 'light',
                  }"
                  :style="{ width: '110px' }">
                  <BkCheckbox
                    v-model="isFilter"
                    :disabled="!checkNum">
                    {{ t('仅显示已选内容') }}
                  </BkCheckbox>
                </div>
                <BkInput
                  v-model="searchValue"
                  class="ml-12"
                  :placeholder="t('搜索实例')"
                  :style="{ width: '298px' }"
                  type="search" />
              </div>
            </div>
          </template>
          <BkTable
            border
            :data="isFilter ? checkedInstances : formData.instance_list"
            :loading="loading">
            <BkTableColumn
              :resizable="false"
              :width="51">
              <template #header>
                <BkCheckbox
                  v-model="isAllSelected"
                  class="instance-list-checkbox"
                  @change="handleSelectAll" />
              </template>
              <template #default="{ row }: { row: RowData }">
                <BkCheckbox
                  v-model="row.checked"
                  class="instance-list-checkbox"
                  :disabled="row.agentStatus !== 1"
                  @change="handleSelect" />
              </template>
            </BkTableColumn>
            <BkTableColumn
              field="instance_address"
              label="Broker"
              :min-width="200" />
            <BkTableColumn
              field="agentStatus"
              :label="t('主机 Agent 状态')"
              :min-width="200">
              <template #default="{ row }: { row: RowData }">
                <DbStatus
                  v-if="row.agentStatus === 1"
                  theme="success">
                  {{ t('正常') }}
                </DbStatus>
                <DbStatus
                  v-else-if="row.agentStatus === 0"
                  theme="danger">
                  {{ t('异常') }}
                </DbStatus>
                <span v-else>--</span>
              </template>
            </BkTableColumn>
            <BkTableColumn
              field="createAt"
              :label="t('部署时间')"
              :min-width="200"
              sort />
          </BkTable>
        </BkFormItem>
      </BkForm>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        :loading="isSubmitting"
        style="min-width: 88px"
        theme="primary"
        @click="handleConfirm">
        {{ t('提交') }}
      </BkButton>
      <BkButton
        style="min-width: 88px"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>
<script setup lang="ts">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import KafkaModel from '@services/model/kafka/kafka';
  import KafkaInstanceModel from '@services/model/kafka/kafka-instance';
  import { getKafkaInstanceList } from '@services/source/kafka';

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import { utcDisplayTime } from '@utils';

  interface RowData
    extends Pick<KafkaInstanceModel, 'instance_address' | 'bk_cloud_id' | 'bk_host_id' | 'ip' | 'port'> {
    agentStatus: number;
    checked: boolean; // Add checked state for selection
    createAt: string;
  }

  interface Props {
    data: KafkaModel;
  }

  const props = defineProps<Props>();

  const isShow = defineModel<boolean>('isShow', {
    required: true,
  });

  const { t } = useI18n();

  let tippyIns: Instance | undefined;
  const formRef = useTemplateRef('form');
  const rootRef = useTemplateRef('root');
  const popRef = useTemplateRef('pop');
  const formData = reactive({
    instance_list: [] as RowData[],
    throttle_rate: 50000000,
    topics: ['*'],
  });
  const isFilter = ref(false);
  const searchValue = ref('');
  const isAllSelected = ref(true);
  const checkNum = computed(() => formData.instance_list.filter((item) => item.checked).length);
  const checkedInstances = computed(() => formData.instance_list.filter((item) => item.checked));

  const { loading, run: getInstanceList } = useRequest(getKafkaInstanceList, {
    manual: true,
    onSuccess: (data) => {
      formData.instance_list = data.results.map((broker) => ({
        ...broker,
        agentStatus: broker.host_info.alive,
        checked: true, // 默认全选
        createAt: utcDisplayTime(broker.create_at),
      }));
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    cluster_id: number;
    instance_info: {
      agent_status: number;
      create_at: string;
      intance_address: string;
    }[];
    instance_list: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port: number;
    }[];
    throttle_rate: number;
    topics: string[];
  }>(TicketTypes.KAFKA_REBALANCE, {
    onSuccess() {
      isShow.value = false;
    },
  });

  watch(
    isShow,
    () => {
      if (isShow.value) {
        getInstanceList({
          cluster_id: props.data?.id,
          extra: 1,
          role: 'broker',
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch(searchValue, (value) => {
    if (value) {
      formData.instance_list = formData.instance_list.filter((item) => item.instance_address.includes(value));
    } else {
      getInstanceList({
        cluster_id: props.data?.id,
        extra: 1,
        role: 'broker',
      });
    }
  });

  const handleSelect = () => {
    isAllSelected.value = formData.instance_list.every((item) => item.checked);
  };

  const handleSelectAll = (checked: boolean) => {
    formData.instance_list.forEach((row) => {
      Object.assign(row, {
        checked,
      });
    });
  };

  const handleShowTips = () => {
    tippyIns?.show();
  };

  const handleConfirm = () => {
    const valid = formRef.value?.validate();
    if (!valid) {
      return;
    }
    const selectedInstances = formData.instance_list.filter((item) => item.checked);
    createTicketRun({
      details: {
        cluster_id: props.data.id,
        instance_info: selectedInstances.map((item) => ({
          agent_status: item.agentStatus,
          create_at: item.createAt,
          intance_address: item.instance_address,
        })),
        instance_list: selectedInstances.map((item) => ({
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          ip: item.ip,
          port: item.port,
        })),
        throttle_rate: formData.throttle_rate,
        topics: formData.topics,
      },
    });
  };

  const handleCancel = () => {
    Object.assign(formData, {
      instance_list: [],
      throttle_rate: 500000,
      topics: ['*'],
    });
    isShow.value = false;
    window.changeConfirm = false;
  };

  onMounted(() => {
    nextTick(() => {
      if (rootRef.value !== null) {
        tippyIns = tippy(rootRef.value as SingleTarget, {
          appendTo: () => document.body,
          arrow: true,
          content: popRef.value,
          hideOnClick: true,
          interactive: true,
          maxWidth: 'none',
          offset: [0, 10],
          placement: 'top',
          theme: 'light',
          trigger: 'manual',
          zIndex: 9998,
        });
      }
    });
  });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  });
</script>
<style lang="less">
  .kafka-topic-sideslider {
    .kafka-topic-header {
      position: relative;
      display: flex;
      height: 22px;
      padding-left: 9px;
      margin-left: 16px;
      font-family: MicrosoftYaHei, sans-serif;
      font-size: 14px;
      line-height: 22px;
      letter-spacing: 0;
      color: #979ba5;

      &::before {
        position: absolute;
        top: 4px;
        left: 0;
        width: 1px;
        height: 14px;
        background-color: #979ba580;
        content: '';
      }
    }

    .kafka-topic-main {
      padding: 18px 24px;
    }

    .kafka-topic-group {
      display: flex;

      .kafka-topic-group-item {
        flex: 1;
      }

      .kafka-topic-group-item:not(:first-child) {
        margin-left: 72px;
      }
    }

    .flex-center {
      display: flex;
      align-items: center;
    }

    .instance-list-form-item {
      display: flex;
      align-items: center;
      justify-content: space-between;

      .instance-list-label {
        width: fit-content;
        font-weight: 400;
      }

      .instance-list-sub-title {
        font-size: 12px;
      }
    }

    .topics-tip {
      display: flex;
      padding: 3px 7px;
      line-height: 24px;
      flex-direction: column;

      div {
        display: flex;
        align-items: center;

        .circle-dot {
          display: inline-block;
          width: 4px;
          height: 4px;
          margin-right: 6px;
          background-color: #63656e;
          border-radius: 50%;
        }
      }
    }

    .instance-list-checkbox {
      position: relative;
      top: 4px;
      left: 2px;
    }
  }
</style>
