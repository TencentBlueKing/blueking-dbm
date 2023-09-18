<template>
  <DbForm
    ref="formRef"
    class="scale-up-form"
    form-type="vertical"
    :model="formdata"
    :rules="rules">
    <BkFormItem
      :label="$t('Master扩容至')"
      property="master">
      <BkInput
        v-model="formdata.master"
        v-bk-tooltips="{
          content: $t('可扩容数量已达上限max_Master数_master_运维节点数_mnt', {
            max: masterScaleUpLimitMax,
            master: data.spider_master.length,
            mnt: data.spider_mnt.length
          }),
          disabled: masterScaleUpLimit.max
        }"
        :disabled="!masterScaleUpLimit.max"
        :max="masterScaleUpLimit.max"
        :min="masterScaleUpLimit.min"
        type="number" />
      <div class="tips">
        <span>{{ $t('当前规格') }}：</span>
        <SpecInfo :data="masterSpecInfo" />
        <span class="spec-count">
          （
          <strong>{{ masterSpecInfo.count }}</strong>
          {{ $t('台') }}
          ）
        </span>
      </div>
    </BkFormItem>
    <BkFormItem
      :label="$t('Slave扩容至')"
      property="slave">
      <BkInput
        v-model="formdata.slave"
        v-bk-tooltips="{
          content: $t('当前集群没有可扩容Slave'),
          disabled: hasSpiderSlave
        }"
        :disabled="!hasSpiderSlave"
        :max="slaveScaleUpLimit.max"
        :min="slaveScaleUpLimit.min"
        type="number" />
      <div
        v-if="slaveSpecInfo"
        class="tips">
        <span>{{ $t('当前规格') }}：</span>
        <SpecInfo :data="slaveSpecInfo" />
        <span class="spec-count">
          （
          <strong>{{ slaveSpecInfo.count }}</strong>
          {{ $t('台') }}
          ）
        </span>
      </div>
    </BkFormItem>
  </DbForm>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';

  import type TendbClusterModel from '@services/model/spider/tendbCluster';
  import { createTicket } from '@services/ticket';

  import { useTicketMessage } from '@hooks';

  import SpecInfo from './SpecInfo.vue';

  import { t } from '@/locales';
  import { useGlobalBizs } from '@/stores';

  interface Props {
    data: TendbClusterModel,
  }

  const props = defineProps<Props>();
  const isChange = defineModel<boolean>('isChange', { required: true });

  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const masterScaleUpLimitMax = 37;
  const formRef = ref();
  const formdata = ref({
    master: '',
    slave: '',
  });
  const initFormdata = JSON.stringify(formdata.value);
  const masterScaleUpLimit = computed(() => {
    const min = props.data.spider_master.length + 1;
    const { spider_master: master, spider_mnt: mnt } = props.data;
    const masterCount = master.length;
    const mntCount = mnt.length;

    // 后端提供规则，spider_master + spider_mnt <= 37
    return {
      min,
      max: masterCount + mntCount < masterScaleUpLimitMax ? masterScaleUpLimitMax - mntCount : 0,
    };
  });
  const slaveScaleUpLimit = computed(() => ({
    min: props.data.spider_slave.length + 1,
    max: 1024,
  }));
  const masterSpecInfo = computed(() => props.data.spider_master[0].spec_config);
  const slaveSpecInfo = computed(() => props.data.spider_slave[0]?.spec_config);
  const hasSpiderSlave = computed(() => props.data.spider_slave.length > 0);
  const rules = {
    master: [
      {
        validator: (value: number | string) => {
          // 没有可扩容 master 则直接返回 true
          const { min, max } = masterScaleUpLimit.value;
          if (max === 0) return true;

          const num = Number(value);
          return min <= num && num <= max;
        },
        message: t('请输入min_max', masterScaleUpLimit.value),
        trigger: 'blur',
      },
    ],
    slave: [
      {
        validator: (value: number | string) => {
          // 没有可扩容 slave 则直接返回 true
          if (!hasSpiderSlave.value) return true;

          const { min, max } = slaveScaleUpLimit.value;
          const num = Number(value);
          return min <= num && num <= max;
        },
        message: t('请输入min_max', slaveScaleUpLimit.value),
        trigger: 'blur',
      },
    ],
  };

  watch(formdata, () => {
    isChange.value = (JSON.stringify(formdata.value) !== initFormdata);
  }, { deep: true });

  defineExpose({
    submit() {
      return formRef.value.validate()
        .then(() => {
          const subTitle = () => (
            <>
              <p>
                {
                  t('name机器数量将从n台升级至m台', {
                    n: props.data.spider_master.length,
                    m: formdata.value.master,
                    name: 'Master ',
                  })
                }
              </p>
              {
                formdata.value.slave
                  ? (
                    <p>
                      {
                        t('name机器数量将从n台升级至m台', {
                          n: props.data.spider_slave.length,
                          m: formdata.value.slave,
                          name: 'Slave ',
                        })
                      }
                    </p>
                  ) : null
              }
            </>
          );
          return new Promise((resolve, reject) => {
            InfoBox({
              title: t('确认扩容【name】集群', { name: props.data.cluster_name }),
              subTitle: subTitle(),
              confirmText: t('确认'),
              cancelText: t('取消'),
              headerAlign: 'center',
              contentAlign: 'center',
              footerAlign: 'center',
              onClosed: () => reject(),
              onConfirm: () => {
                const { id } = props.data;
                const infos = [
                  {
                    cluster_id: id,
                    add_spider_role: 'spider_master',
                    resource_spec: {
                      spider_ip_list: {
                        ...masterSpecInfo.value,
                        count: formdata.value.master,
                      },
                    },
                  },
                ];

                if (Number(formdata.value.slave) > 0) {
                  infos.push({
                    cluster_id: id,
                    add_spider_role: 'spider_slave',
                    resource_spec: {
                      spider_ip_list: {
                        ...slaveSpecInfo.value,
                        count: formdata.value.slave,
                      },
                    },
                  });
                }
                createTicket({
                  bk_biz_id: currentBizId,
                  ticket_type: 'TENDBCLUSTER_SPIDER_ADD_NODES',
                  details: {
                    ip_source: 'resource_pool',
                    infos,
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
.scale-up-form {
  padding: 28px 40px 24px;

  .tips {
    display: flex;
    align-items: center;
    font-size: 12px;
  }
}
</style>
