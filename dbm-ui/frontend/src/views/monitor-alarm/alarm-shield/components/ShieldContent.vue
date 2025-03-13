<template>
  <BkPopover
    disabled
    :popover-delay="[100, 0]"
    width="430">
    <div class="shield-content-main">
      <div
        v-for="item in renderList"
        :key="item.id">
        <div
          v-if="item.getValue()"
          class="content-item">
          <div class="title">
            <span>{{ item.title }}</span>
            <span class="ml-4 mr-4">:</span>
          </div>
          <div
            v-overflow-tips
            class="content">
            {{ item.getValue() }}
          </div>
        </div>
      </div>
    </div>
    <template #content>
      <div
        v-for="item in renderList"
        :key="item.id">
        <div
          v-if="item.getValue()"
          class="shield-content-item">
          <div class="title">
            <span>{{ item.title }}</span>
            <span class="ml-4 mr-4">:</span>
          </div>
          <div class="content">{{ item.getValue() }}</div>
        </div>
      </div>
    </template>
  </BkPopover>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import AlarmShieldModel from '@services/model/monitor/alarm-shield';

  import { useGlobalBizs } from '@stores';

  interface Props {
    data: AlarmShieldModel['dimension_config'];
    // 避免请求爆炸
    strategyMap: Record<number, string>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { bizs } = useGlobalBizs();

  const severityMap = {
    1: t('致命'),
    2: t('告警'),
    3: t('提醒'),
  };

  // const showTip = computed(() => renderList.value.filter((item) => item.content !== '').length > 2);
  const bizsMap = computed(() =>
    bizs.reduce<Record<number, string>>((results, item) => {
      Object.assign(results, {
        [item.bk_biz_id]: item.name,
      });
      return results;
    }, {}),
  );

  const renderList = computed(() => [
    {
      getValue: () => {
        // eslint-disable-next-line no-underscore-dangle
        const severity = props.data._severity || props.data.level || '';
        if (severity !== undefined) {
          if (typeof severity === 'number') {
            return severityMap[severity as keyof typeof severityMap];
          } else if (Array.isArray(severity)) {
            return severity.map((item) => severityMap[item as keyof typeof severityMap]).join(' , ');
          }
        }

        return '';
      },
      id: 'severity',
      title: t('告警级别'),
    },
    {
      getValue: () =>
        props.data.ip ||
        props.data?.bk_target_ip?.map((item) => item.bk_target_ip).join(',') ||
        props.data.dimension_conditions?.find((item) => item.key === 'instance_host')?.value.join(' , ') ||
        '',
      id: 'ip',
      title: t('告警主机'),
    },
    {
      getValue: () => props.data.dimension_conditions?.find((item) => item.key === 'instance')?.value.join(' , ') || '',
      id: 'instance',
      title: t('告警实例'),
    },
    {
      getValue: () =>
        props.data['tags.cluster_domain'] ||
        props.data.dimension_conditions?.find((item) => item.key === 'cluster_domain')?.value.join(' , ') ||
        '',
      id: 'cluster',
      title: t('所属集群'),
    },
    {
      getValue: () => {
        const biz =
          props.data['tags.appid'] ||
          props.data.dimension_conditions?.find((item) => item.key === 'appid')?.value.join(' , ') ||
          '';
        return biz ? `${bizsMap.value[Number(biz)]} (#${biz})` : '';
      },
      id: 'biz',
      title: t('所属业务'),
    },
    {
      getValue: () =>
        props.data.dimension_conditions?.find((item) => item.key === 'instance_role')?.value.join(' , ') || '',
      id: 'role',
      title: t('角色'),
    },
    {
      // eslint-disable-next-line no-underscore-dangle
      getValue: () => props.data._alert_message || '',
      id: 'condition',
      title: t('触发条件'),
    },
    {
      getValue: () => {
        const strategyIdList = (props.data.strategy_id as number[]) || [];
        return strategyIdList.length ? strategyIdList.map((id) => props.strategyMap[id]).join(' , ') : '';
      },
      id: 'strategy',
      title: t('策略名称'),
    },
  ]);
</script>
<style lang="less" scoped>
  .shield-content-main {
    display: flex;
    width: 100%;
    flex-direction: column;
    // max-height: 45px;
    overflow: hidden;
    cursor: pointer;

    .content-item {
      display: flex;
      width: 100%;
      min-height: 22px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;

      .content {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        flex: 1;
      }
    }
  }
</style>
<style lang="less">
  .shield-content-item {
    display: flex;
    width: 100%;
    min-height: 22px;
    flex-wrap: wrap;

    .content {
      flex: 1;
      overflow: hidden;
    }
  }
</style>
