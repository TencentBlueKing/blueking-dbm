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
    <span v-if="data.remark">
      <span v-if="onlyRemark">{{ data.remark }}</span>
      <span v-else>，{{ t('备注') }}：{{ data.remark }}</span>
    </span>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';
  import { MachineEvents, machineEventsDisplayMap } from '@common/const/machineEvents';

  import { getBusinessHref } from '@utils';

  interface Props {
    data: {
      bk_biz_id: number;
      bk_biz_name?: string;
      event: MachineEvents;
      remark: string;
      ticket?: number;
      ticket_type: string;
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
  const onlyRemark = computed(() =>
    [MachineEvents.HOST_ATTRIBUTE, MachineEvents.REMOVE_HOST, MachineEvents.RESOURCE_OWNER].includes(props.data.event),
  );

  const bizName = computed(() => props.data.bk_biz_name || globalBizsStore.bizIdMap.get(props.data.bk_biz_id)?.name);

  const machineEventsMap = computed(() => {
    const returnResourceTextMap: Record<string, string> = {
      [TicketTypes.RECYCLE_OLD_HOST]: t('已下架主机检测无异常，自动转入资源池再利用'),
      [TicketTypes.RESOURCE_IMPORT]: t('从其它池手动退回资源池'),
    };

    return {
      [MachineEvents.APPLY_RESOURCE]: t('从资源池申领主机'),
      [MachineEvents.HOST_ATTRIBUTE]: '',
      [MachineEvents.IMPORT_RESOURCE]: t('从「n」业务 CMDB空闲机模块导入', { n: bizName.value }),
      [MachineEvents.RECYCLED]: t('从系统中删除主机记录，主机同步转入 CMDB「n」待回收模块', { n: bizName.value }),
      [MachineEvents.REMOVE_HOST]: '',
      [MachineEvents.RESOURCE_OWNER]: '',
      [MachineEvents.RETURN_RESOURCE]:
        returnResourceTextMap[props.data.ticket_type] || machineEventsDisplayMap[props.data.event],
      // [MachineEvents.TO_DIRTY]: machineEventsDisplayMap[props.data.event],
      [MachineEvents.TO_FAULT]: t('其它池手动转入故障池'),
      [MachineEvents.TO_RECYCLE]: t('其它池手动转入待回收池'),
      [MachineEvents.UNDO_IMPORT]: t('退回「n」业务 CMDB 空闲机模块', { n: bizName.value }),
    };
  });

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
