<template>
  <BkDialog
    ext-cls="sqlserver-cluster-reset"
    :is-show="isShow"
    theme="primary"
    :title="t('重置集群')"
    @closed="() => (isShow = false)"
    @confirm="handleConfirm">
    <BkAlert
      closable
      theme="warning"
      :title="t('集群的数据将会被全部清空')" />
    <BkForm
      ref="formRef"
      class="reset-form"
      label-width="80"
      :model="formData">
      <BkFormItem
        class="mt-8"
        :label="t('当前域名')">
        {{ props.data.master_domain }}
      </BkFormItem>
      <BkComposeFormItem>
        <BkFormItem
          class="mb-24"
          :label="t('新域名')"
          property="newClusterName"
          :rules="domainRule">
          <div class="new-cluster-name">
            <span class="domain-text mr-4">{{ domainInfo.prefix }}</span>
            <BkInput
              v-model="formData.newClusterName"
              v-bk-tooltips="{
                trigger: 'click',
                theme: 'light',
                placement: 'top',
                content: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
              }"
              class="cluster-name-input"
              :placeholder="t('请输入')" />
            <span class="domain-text ml-4">{{ domainInfo.suffix }}</span>
          </div>
        </BkFormItem>
      </BkComposeFormItem>
    </BkForm>
  </BkDialog>
</template>

<script setup lang="ts" generic="T extends SqlServerSingleClusterModel | SqlServerHaClusterModel">
  import { Form } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import SqlServerHaClusterModel from '@services/model/sqlserver/sqlserver-ha-cluster';
  import SqlServerSingleClusterModel from '@services/model/sqlserver/sqlserver-single-cluster';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';
  import { nameRegx } from '@common/regex';

  interface Props {
    data: T;
  }

  const props = defineProps<Props>();
  const isShow = defineModel<boolean>('isShow', {
    required: true,
  });

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const domainRule = [
    {
      required: true,
      message: t('必填项'),
      trigger: 'change',
    },
    {
      message: t('最大长度为m', { m: 63 }),
      trigger: 'blur',
      validator: (val: string) => val.length <= 63,
    },
    {
      message: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
      trigger: 'blur',
      validator: (val: string) => nameRegx.test(val),
    },
  ];

  const formRef = ref<InstanceType<typeof Form>>();
  const formData = reactive({
    newClusterName: '',
  });

  const domainInfo = computed(() => {
    const masterDomain = props.data.master_domain;
    const domainItemList = masterDomain.split('.');

    return {
      prefix: `${domainItemList[0]}.`,
      suffix: `.${domainItemList[2]}.${domainItemList[3]}`,
    };
  });

  const getNewDomain = (domain: string, newClusterName: string) => {
    const domainItemList = domain.split('.');
    domainItemList[1] = newClusterName;
    return domainItemList.join('.');
  };

  const handleConfirm = async () => {
    await formRef.value!.validate();

    const { data } = props;
    const { newClusterName } = formData;
    const infoItem = {
      cluster_id: data.id,
      new_cluster_name: newClusterName,
      new_immutable_domain: getNewDomain(data.master_domain, newClusterName),
    };
    if (data.cluster_type === ClusterTypes.SQLSERVER_HA) {
      Object.assign(infoItem, {
        new_slave_domain: getNewDomain(data.slave_domain, newClusterName),
      });
    }

    createTicket({
      bk_biz_id: props.data.bk_biz_id,
      ticket_type: TicketTypes.SQLSERVER_RESET,
      details: {
        infos: [infoItem],
      },
    }).then((createTicketResult) => {
      ticketMessage(createTicketResult.id);
      isShow.value = false;
    });
  };
</script>

<style lang="less">
  .sqlserver-cluster-reset {
    .reset-form {
      .bk-form-label,
      .bk-form-content {
        font-size: 12px;
      }

      .new-cluster-name {
        display: flex;

        .cluster-name-input {
          flex: 1;
        }

        .domain-text {
          flex-shrink: 0;
        }
      }
    }
  }
</style>
