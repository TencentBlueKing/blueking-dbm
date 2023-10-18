<template>
  <DbForm
    ref="formRef"
    class="capacity-form"
    form-type="vertical"
    :model="formdata">
    <div class="spec-box mb-24">
      <table>
        <tr>
          <td>{{ t('当前规格') }}:</td>
          <td>{{ data.cluster_spec.spec_name }}</td>
          <td>{{ t('变更后规格') }}:</td>
          <td>{{ currentSpec?.spec_name ?? '--' }}</td>
        </tr>
        <tr>
          <td>{{ t('当前容量') }}:</td>
          <td>{{ data.cluster_capacity }} G</td>
          <td>{{ t('变更后容量') }}:</td>
          <td>{{ currentSpec?.cluster_capacity ?? 0 }} G</td>
        </tr>
      </table>
    </div>
    <SpecPlanSelector
      :cloud-id="data.bk_cloud_id"
      cluster-type="tendbcluster"
      machine-type="remote"
      :plan-form-item-props="{
        property: 'specId',
        required: true
      }"
      @change="handlePlanChange" />
    <BkFormItem
      class="mt-24"
      :label="t('数据校验')"
      property="need_checksum"
      required>
      <BkSwitcher
        v-model="formdata.need_checksum"
        theme="primary" />
    </BkFormItem>
    <template v-if="formdata.need_checksum">
      <BkFormItem
        :label="t('校验时间')"
        property="trigger_checksum_type"
        required>
        <BkRadioGroup v-model="formdata.trigger_checksum_type">
          <BkRadio label="now">
            {{ t('立即执行') }}
          </BkRadio>
          <BkRadio label="timer">
            {{ t('定时执行') }}
          </BkRadio>
        </BkRadioGroup>
      </BkFormItem>
      <BkFormItem
        v-if="formdata.trigger_checksum_type === 'timer'"
        :label="t('定时执行')"
        property="trigger_checksum_time"
        required>
        <BkDatePicker
          v-model="formdata.trigger_checksum_time"
          style="width: 360px"
          type="datetime" />
      </BkFormItem>
    </template>
  </DbForm>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import dayjs from 'dayjs';

  // TODO INTERFACE
  import type TendbClusterModel from '@services/model/spider/tendbCluster';
  import { createTicket } from '@services/ticket';

  import { useTicketMessage } from '@hooks';

  import SpecPlanSelector, {
    type IRowData,
  }  from '@components/cluster-spec-plan-selector/Index.vue';

  import { t } from '@/locales';
  import { useGlobalBizs } from '@/stores';

  interface Props {
    data: TendbClusterModel,
  }

  const props = defineProps<Props>();
  const isChange = defineModel<boolean>('isChange', { required: true });

  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const formRef = ref();
  const formdata = ref({
    specId: '' as number | string,
    need_checksum: false,
    trigger_checksum_type: 'timer',
    trigger_checksum_time: dayjs().format('YYYY-MM-DD HH:mm:ss'),
  });
  const initformdata = JSON.stringify(formdata.value);
  const currentSpec = shallowRef<IRowData>();

  watch(formdata, () => {
    isChange.value = (JSON.stringify(formdata.value) !== initformdata);
  }, { deep: true });

  const handlePlanChange = (specId: number, specData: IRowData) => {
    currentSpec.value = specData;
    formdata.value.specId = specId;
  };

  defineExpose({
    submit() {
      return formRef.value.validate()
        .then(() => {
          const subTitle = () => (
            <>
              <p class="pb-8">{props.data.cluster_name}</p>
              <p class="pb-8">
                {
                  t('容量将从old变更至new', {
                    old: `${props.data.cluster_capacity} G`,
                    new: `${currentSpec.value?.cluster_capacity ?? 0} G`,
                  })
                }
              </p>
            </>
          );

          const data: Record<string, any> = { ...formdata.value };
          delete data.specId;
          return new Promise((resolve, reject) => {
            InfoBox({
              title: t('确认变更集群容量'),
              subTitle: subTitle(),
              confirmText: t('确认'),
              cancelText: t('取消'),
              headerAlign: 'center',
              contentAlign: 'center',
              footerAlign: 'center',
              onClosed: () => reject(),
              onConfirm: () => {
                createTicket({
                  ticket_type: 'TENDBCLUSTER_NODE_REBALANCE',
                  bk_biz_id: currentBizId,
                  remark: '',
                  details: {
                    ...formdata.value,
                    infos: [
                      {
                        bk_cloud_id: props.data.bk_cloud_id,
                        cluster_id: props.data.id,
                        db_module_id: props.data.db_module_id,
                        cluster_shard_num: props.data.cluster_shard_num,
                        remote_shard_num: props.data.remote_shard_num,
                        resource_spec: {
                          backend_group: {
                            spec_id: currentSpec.value?.spec_id,
                            count: currentSpec.value?.machine_pair,
                            affinity: '',
                          },
                        },
                      },
                    ],
                  },
                })
                  .then((data) => {
                    ticketMessage(data.id);
                    resolve('success');
                    isChange.value = false;
                  })
                  .catch(() => {
                    reject();
                  });
              },
            });
          });
        });
    },
    cancel() {
      isChange.value = false;
    },
  });
</script>

<style lang="less" scoped>
.capacity-form {
  padding: 28px 40px 24px;

  :deep(.bk-form-label){
    font-weight: bold;
  }

  .spec-box{
    width: 100%;
    padding: 16px 0;
    font-size: 12px;
    line-height: 18px;
    background-color: #FAFBFD;

    table{
      width: 100%;
      table-layout: fixed;
    }

    td{
      height: 18px;
      padding-left: 16px;

      &:nth-child(2n+1){
        text-align: right;
      }
    }
  }

  .tips {
    display: flex;
    align-items: center;
    font-size: 12px;
  }
}
</style>
