<template>
  <div>
    <span v-if="onlyText">
      {{ machineEventsMap[data.event] }}
    </span>
    <I18nT
      v-else
      :keypath="ticketManagekeyPathMap[data.event as keyof typeof ticketManagekeyPathMap]"
      tag="span">
      <BkButton
        text
        theme="primary"
        @click="handleToTicketManage">
        {{ data.ticket }}
      </BkButton>
      <RouterLink
        target="_blank"
        :to="{
          name: 'bizTicketManage',
          params: {
            ticketId: data.ticket,
          },
          query: {
            ids: data.ticket,
          },
        }">
        {{ data.ticket }}
      </RouterLink>
    </I18nT>
    <span v-if="data.remark"> ，{{ t('备注') }}：{{ data.remark }} </span>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useGlobalBizs } from '@stores';

  import { MachineEvents, machineEventsDisplayMap } from '@common/const/machineEvents';

  import { getBusinessHref } from '@utils';

  interface Props {
    data: {
      bk_biz_id: number;
      bk_biz_name?: string;
      event: MachineEvents;
      remark: string;
      ticket?: number;
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const router = useRouter();
  const globalBizsStore = useGlobalBizs();

  const ticketManagekeyPathMap: Record<MachineEvents.TO_FAULT | MachineEvents.TO_RECYCLE, string> = {
    [MachineEvents.TO_FAULT]: '已下架主机自动转入故障池（关联单据：xxxx）',
    [MachineEvents.TO_RECYCLE]: '已下架主机自动转入待回收池（关联单据：xxxx）',
  };

  const onlyText = computed(
    () => !([MachineEvents.TO_FAULT, MachineEvents.TO_RECYCLE].includes(props.data.event) && props.data.ticket),
  );

  const bizName = computed(() => props.data.bk_biz_name || globalBizsStore.bizIdMap.get(props.data.bk_biz_id)?.name);

  const machineEventsMap = computed(() => ({
    [MachineEvents.APPLY_RESOURCE]: machineEventsDisplayMap[props.data.event],
    [MachineEvents.IMPORT_RESOURCE]: t('从「n」业务 CMDB空闲机模块导入', { n: bizName.value }),
    [MachineEvents.RECYCLED]: t('回收到「n」业务 CMDB 待回收模块', { n: bizName.value }),
    [MachineEvents.RETURN_RESOURCE]: props.data.ticket ? t('已下架主机退回资源池再利用') : t('故障池主机转回资源池'),
    [MachineEvents.TO_DIRTY]: machineEventsDisplayMap[props.data.event],
    [MachineEvents.TO_FAULT]: t('从资源池手动转入'),
    [MachineEvents.TO_RECYCLE]: t('从其他池转入待回收池'),
    [MachineEvents.UNDO_IMPORT]: t('退回「n」业务 CMDB 空闲机模块', { n: bizName.value }),
  }));

  const handleToTicketManage = () => {
    const routeInfo = router.resolve({
      name: 'bizTicketManage',
      params: {
        ticketId: props.data.ticket,
      },
      query: {
        ids: props.data.ticket,
      },
    });
    const href = getBusinessHref(routeInfo.href, props.data.bk_biz_id);
    window.open(href, '_blank');
  };
</script>
