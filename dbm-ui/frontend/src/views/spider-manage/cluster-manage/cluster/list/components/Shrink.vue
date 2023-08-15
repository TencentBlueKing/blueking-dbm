<template>
  <DbForm
    ref="formRef"
    class="shrink-form"
    form-type="vertical"
    :model="formdata"
    :rules="rules">
    <BkFormItem
      :label="$t('Master缩容至')"
      property="master">
      <BkInput
        v-model="formdata.master"
        v-bk-tooltips="{
          content: $t('可缩容数量已达上限_至少保留n台', { n: masterShrinkLimit.min }),
          disabled: isAllowShrinkMaster
        }"
        :disabled="!isAllowShrinkMaster"
        :max="masterShrinkLimit.max"
        :min="masterShrinkLimit.min"
        type="number" />
      <div class="tips">
        <span>{{ $t('当前规格') }}：</span>
        <SpecInfo :data="masterSpecInfo" />
        <span class="spec-count">
          （
          <strong>{{ masterSpecInfo.count }}</strong>
          {{ $t('台') }}
          ），{{ $t('至少保留n台', { n: masterShrinkLimit.min }) }}
        </span>
      </div>
    </BkFormItem>
    <BkFormItem
      :label="$t('Slave缩容至')"
      property="slave">
      <BkInput
        v-model="formdata.slave"
        v-bk-tooltips="spiderSlaveTips"
        :disabled="!isAllowShrinkSlave"
        :max="slaveShrinkLimit.max"
        :min="slaveShrinkLimit.min"
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
          ），{{ $t('至少保留n台', { n: slaveShrinkLimit.min }) }}
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

  const formRef = ref();
  const formdata = ref({
    master: '',
    slave: '',
  });
  const initFormdata = JSON.stringify(formdata.value);
  const masterShrinkLimit = computed(() => ({
    min: 2, // 至少保留 2 台
    max: props.data.spider_master.length - 1,
  }));
  const slaveShrinkLimit = computed(() => ({
    min: 1, // 至少保留 1 台
    max: props.data.spider_slave.length - 1,
  }));
  const masterSpecInfo = computed(() => props.data.spider_master[0].spec_config);
  const slaveSpecInfo = computed(() => props.data.spider_slave[0]?.spec_config);
  const isAllowShrinkMaster = computed(() => props.data.spider_master.length > masterShrinkLimit.value.min);
  const isAllowShrinkSlave = computed(() => props.data.spider_slave.length > slaveShrinkLimit.value.min);
  const spiderSlaveTips = computed(() => {
    const hasSlave = props.data.spider_slave.length > 0;
    if (hasSlave) {
      return {
        content: t('可缩容数量已达上限_至少保留n台', { n: slaveShrinkLimit.value.min }),
        disabled: isAllowShrinkSlave.value,
      };
    }

    return {
      content: t('当前集群没有可缩容Slave'),
      disabled: false,
    };
  });
  const rules = {
    master: [
      {
        validator: (value: number | string) => {
          // 禁用则不需校验
          if (isAllowShrinkMaster.value === false) return true;

          const num = Number(value);
          const { min, max } = masterShrinkLimit.value;
          return min <= num && num <= max;
        },
        message: t('请输入min_max', masterShrinkLimit.value),
        trigger: 'blur',
      },
    ],
    slave: [
      {
        validator: (value: number | string) => {
          // 没有可缩容 slave 则直接返回 true
          if (props.data.spider_slave.length === 0) return true;

          const { min, max } = slaveShrinkLimit.value;
          const num = Number(value);
          return min <= num && num <= max;
        },
        message: t('请输入min_max', slaveShrinkLimit.value),
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
              {
                formdata.value.master
                  ? (
                    <p>
                      {
                        t('name机器数量将从n台缩减至m台', {
                          n: props.data.spider_master.length,
                          m: formdata.value.master,
                          name: 'Master ',
                        })
                      }
                    </p>
                  ) : null
              }
              {
                formdata.value.slave
                  ? (
                    <p>
                      {
                        t('name机器数量将从n台缩减至m台', {
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
              title: t('确认缩容【name】集群', { name: props.data.cluster_name }),
              subTitle: subTitle(),
              confirmText: t('确认'),
              cancelText: t('取消'),
              headerAlign: 'center',
              contentAlign: 'center',
              footerAlign: 'center',
              onClosed: () => reject(),
              onConfirm: () => {
                const { id } = props.data;
                const infos: {
                  cluster_id: number,
                  reduce_spider_role: 'spider_master' | 'spider_slave',
                  spider_reduced_to_count: number,
                }[] = [];

                const masterCount = Number(formdata.value.master);
                if (masterCount > 0) {
                  infos.push({
                    cluster_id: id,
                    reduce_spider_role: 'spider_master',
                    spider_reduced_to_count: masterCount,
                  });
                }
                const slaveCount = Number(formdata.value.slave);
                if (slaveCount > 0) {
                  infos.push({
                    cluster_id: id,
                    reduce_spider_role: 'spider_slave',
                    spider_reduced_to_count: slaveCount,
                  });
                }
                createTicket({
                  bk_biz_id: currentBizId,
                  ticket_type: 'TENDBCLUSTER_SPIDER_REDUCE_NODES',
                  details: {
                    is_safe: true,
                    infos,
                  },
                })
                  .then((data) => {
                    ticketMessage(data.id);
                    resolve('success');
                  })
                  .catch(() => {
                    reject();
                  });
              },
            });
          });
        });
    },
  });
</script>

<style lang="less" scoped>
.shrink-form {
  padding: 28px 40px 24px;

  .tips {
    display: flex;
    align-items: center;
    font-size: 12px;
  }
}
</style>
