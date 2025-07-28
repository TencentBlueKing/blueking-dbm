<template>
  <div class="sqlserver-rollback-page">
    <SmartAction>
      <BkAlert
        closable
        theme="info"
        :title="
          t('新建一个单节点实例，通过全备 +binlog 的方式，将数据库恢复到过去的某一时间点或者某个指定备份文件的状态。')
        " />
      <DbForm
        ref="form"
        class="mt-16 mb-24 toolbox-form"
        form-type="vertical"
        :model="formData">
        <BkFormItem
          :label="t('构造类型')"
          required
          @change="handleChange">
          <BkRadioGroup v-model="formData.is_local">
            <BkRadioButton
              label
              style="width: 200px">
              {{ t('原地定点构造') }}
            </BkRadioButton>
            <BkRadioButton
              :label="false"
              style="width: 200px">
              {{ t('定点构造到其他集群') }}
            </BkRadioButton>
          </BkRadioGroup>
        </BkFormItem>
        <BkFormItem
          :label="t('时区')"
          required>
          <TimeZonePicker style="width: 450px" />
        </BkFormItem>
        <Component
          :is="renderCom"
          ref="tableRef" />
        <TicketPayload v-model="formData.payload" />
      </DbForm>
      <template #action>
        <BkButton
          class="w-88"
          :loading="isSubmitting"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <DbPopconfirm
          :confirm-handler="handleReset"
          :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
          :title="t('确认重置页面')">
          <BkButton
            class="ml-8 w-88"
            :disabled="isSubmitting">
            {{ t('重置') }}
          </BkButton>
        </DbPopconfirm>
      </template>
    </SmartAction>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { type Sqlserver } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import RenderLocal from './components/local/Index.vue';
  import RenderOtherCluster from './components/other-cluster/Index.vue';

  const createDefaultFormData = () => ({
    is_local: true,
    payload: createTickePayload(),
  });

  const { t } = useI18n();

  useTicketDetail<Sqlserver.Rollback>(TicketTypes.SQLSERVER_ROLLBACK, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        is_local: details.is_local,
        payload: createTickePayload(ticketDetail),
      });

      nextTick(() => {
        tableRef.value!.setTicketCloneData(details);
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: Sqlserver.Rollback['infos'];
    is_local: boolean;
  }>(TicketTypes.SQLSERVER_ROLLBACK);

  const formRef = useTemplateRef('form');
  const tableRef = useTemplateRef('tableRef');

  const formData = reactive(createDefaultFormData());

  const renderCom = computed(() => (formData.is_local ? RenderLocal : RenderOtherCluster));

  const handleChange = () => {
    tableRef.value!.reset();
  };

  const handleSubmit = async () => {
    await formRef.value!.validate();
    const infos = await tableRef.value!.submit();
    if (infos.length) {
      createTicketRun({
        details: {
          infos,
          is_local: formData.is_local,
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    window.changeConfirm = false;
  };
</script>
<style lang="less">
  .sqlserver-rollback-page {
    .bk-form-label {
      font-weight: bold;
      color: #313238;
    }
  }
</style>
