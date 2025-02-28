<template>
  <BkPopover
    :disabled="!showTip"
    :popover-delay="[100, 0]"
    width="430">
    <div class="shield-content-main">
      <div
        v-for="item in renderList"
        :key="item.id">
        <div
          v-if="item.content"
          class="content-item">
          <div class="title">
            <span>{{ item.title }}</span>
            <span class="ml-4 mr-4">:</span>
          </div>
          <div class="content">{{ item.content }}</div>
        </div>
      </div>
    </div>
    <template #content>
      <div
        v-for="item in renderList"
        :key="item.id">
        <div
          v-if="item.content"
          class="shield-content-item">
          <div class="title">
            <span>{{ item.title }}</span>
            <span class="ml-4 mr-4">:</span>
          </div>
          <div class="content">{{ item.content }}</div>
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

  const renderList = ref([
    {
      content: '',
      id: 'severity',
      title: t('告警级别'),
    },
    {
      content: '',
      id: 'ip',
      title: t('告警主机'),
    },
    {
      content: '',
      id: 'instance',
      title: t('告警实例'),
    },
    {
      content: '',
      id: 'cluster',
      title: t('所属集群'),
    },
    {
      content: '',
      id: 'biz',
      title: t('所属业务'),
    },
    {
      content: '',
      id: 'role',
      title: t('角色'),
    },
    {
      content: '',
      id: 'condition',
      title: t('触发条件'),
    },
    {
      content: '',
      id: 'strategy',
      title: t('策略名称'),
    },
  ]);

  const showTip = computed(() => renderList.value.filter((item) => item.content !== '').length > 2);
  const bizsMap = computed(() =>
    bizs.reduce<Record<number, string>>((results, item) => {
      Object.assign(results, {
        [item.bk_biz_id]: item.name,
      });
      return results;
    }, {}),
  );

  watch(
    () => [props.data, props.strategyMap],
    () => {
      // 告警等级
      // eslint-disable-next-line no-underscore-dangle
      const severity = props.data._severity || props.data.level || '';
      if (severity !== undefined) {
        if (typeof severity === 'number') {
          renderList.value[0].content = severityMap[severity as keyof typeof severityMap];
        } else if (Array.isArray(severity)) {
          renderList.value[0].content = severity
            .map((item) => severityMap[item as keyof typeof severityMap])
            .join(' , ');
        }
      }
      // 主机
      const ip =
        props.data.ip ||
        props.data?.bk_target_ip?.map((item) => item.bk_target_ip).join(',') ||
        props.data.dimension_conditions?.find((item) => item.key === 'instance_host')?.value.join(' , ') ||
        '';
      renderList.value[1].content = ip;
      // 实例
      const instance =
        props.data.dimension_conditions?.find((item) => item.key === 'instance')?.value.join(' , ') || '';
      renderList.value[2].content = instance;
      // 集群
      const cluster =
        props.data['tags.cluster_domain'] ||
        props.data.dimension_conditions?.find((item) => item.key === 'cluster_domain')?.value.join(' , ') ||
        '';
      renderList.value[3].content = cluster;
      // 业务
      const biz =
        props.data['tags.appid'] ||
        props.data.dimension_conditions?.find((item) => item.key === 'appid')?.value.join(' , ') ||
        '';
      renderList.value[4].content = biz ? `${bizsMap.value[Number(biz)]} (#${biz})` : '';
      // 角色
      const role =
        props.data.dimension_conditions?.find((item) => item.key === 'instance_role')?.value.join(' , ') || '';
      renderList.value[5].content = role;
      // 触发条件
      // eslint-disable-next-line no-underscore-dangle
      const condition = props.data._alert_message || '';
      renderList.value[6].content = condition;
      // 告警策略
      const strategyIdList = props.data.strategy_id || [];
      renderList.value[7].content = strategyIdList.length
        ? strategyIdList.map((id) => props.strategyMap[id]).join(' , ')
        : '';
    },
    {
      deep: true,
      immediate: true,
    },
  );
</script>
<style lang="less" scoped>
  .shield-content-main {
    display: flex;
    width: 100%;
    flex-direction: column;
    max-height: 45px;
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
