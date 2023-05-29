<template>
  <div class="recommend-architecture-form">
    <BkForm
      ref="formRef"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('Redis 数据存储用途')"
        property="use"
        required>
        <BkRadioGroup v-model="formData.use">
          <BkRadio label="cache">
            {{ t('缓存：大部分数据带有过期时间, 数据量不会持续增加，QPS 较高，延迟敏感；') }}
          </BkRadio>
          <BkRadio label="storage">
            {{ t('数据主存储：大部分数据不带过期时间, 数据量持续增加，QPS 较低，可接受一定延迟；') }}
          </BkRadio>
        </BkRadioGroup>
      </BkFormItem>
      <BkFormItem
        :label="t('Redis 集群连接方式')"
        property="method"
        required>
        <BkRadioGroup v-model="formData.method">
          <BkRadio label="normal">
            {{ t('普通客户端：Redis Single 连接方式，Slot 与节点映射关系由 Proxy 自动处理；') }}
          </BkRadio>
          <BkRadio label="smart">
            {{
              t('智能客户端：RedisCluster 连接方式，客户端自动维护 Slot 与节点映射关系，客户端自动处理 MOVED 错误；')
            }}
          </BkRadio>
        </BkRadioGroup>
      </BkFormItem>
      <BkFormItem
        :label="t('是否使用较多 hgetall、zrevrange 等 O(n) 命令？')"
        property="complexity"
        required>
        <BkRadioGroup v-model="formData.complexity">
          <BkRadio label="yes">{{ t('是') }}</BkRadio>
          <BkRadio label="no">{{ t('否') }}</BkRadio>
        </BkRadioGroup>
      </BkFormItem>
    </BkForm>
    <div class="mt-36">
      <BkButton
        theme="primary"
        @click="handleGenarate">
        {{ t('生成推荐') }}
      </BkButton>
      <BkButton
        class="ml-8"
        @click="handleClear">
        {{ t('清空') }}
      </BkButton>
    </div>
    <div class="recommend-architecture mt-20">
      <div>{{ t('根据您的需求推荐：') }}</div>
      <div
        v-if="recommendInfo"
        class="recommend-architecture-item">
        <span class="item-text">{{ recommendInfo.text }}{{ t('集群') }}，</span>
        <span>{{ recommendInfo.tipContent.desc }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { Form } from 'bkui-vue';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  import { redisClusterTypes } from '../../../common/const';

  const recommendArchitectrue = defineModel<string>('recommendArchitectrue', {
    required: true,
  });

  const { t } = useI18n();

  const formRef = ref<InstanceType<typeof Form>>();

  const formData = reactive({
    use: '',
    method: '',
    complexity: '',
  });

  watch(
    formData,
    () => {
      recommendArchitectrue.value = '';
    },
    {
      deep: true,
    },
  );

  const recommendInfo = computed(
    () => redisClusterTypes[recommendArchitectrue.value as keyof typeof redisClusterTypes],
  );

  const intersection = (arrayList: ClusterTypes[][]) =>
    arrayList.reduce((prevList, curList) => prevList.filter((value) => curList.includes(value)));

  const handleGenarate = async () => {
    await formRef.value!.validate();
    const { use, method, complexity } = formData;
    const architectrueMap: Record<string, ClusterTypes[]> = {
      cache: [ClusterTypes.PREDIXY_REDIS_CLUSTER, ClusterTypes.TWEMPROXY_REDIS_INSTANCE],
      storage: [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER],
      normal: [
        ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
        ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
        ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
        ClusterTypes.PREDIXY_REDIS_CLUSTER,
      ],
      smart: [ClusterTypes.PREDIXY_REDIS_CLUSTER, ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER],
      yes: [ClusterTypes.PREDIXY_REDIS_CLUSTER, ClusterTypes.TWEMPROXY_REDIS_INSTANCE],
      no: [
        ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
        ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
        ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
        ClusterTypes.PREDIXY_REDIS_CLUSTER,
      ],
    };

    const intersectedArrayList = intersection([
      architectrueMap[use],
      architectrueMap[method],
      architectrueMap[complexity],
    ]);

    if (intersectedArrayList.length === 0) {
      recommendArchitectrue.value = ClusterTypes.PREDIXY_REDIS_CLUSTER;
      return;
    }
    if (intersectedArrayList.length === 1) {
      recommendArchitectrue.value = intersectedArrayList[0] as string;
      return;
    }
    if (
      _.isEqual(
        intersectedArrayList.sort(),
        [ClusterTypes.PREDIXY_REDIS_CLUSTER, ClusterTypes.TWEMPROXY_REDIS_INSTANCE].sort(),
      )
    ) {
      recommendArchitectrue.value = ClusterTypes.PREDIXY_REDIS_CLUSTER;
      return;
    }

    recommendArchitectrue.value = ClusterTypes.PREDIXY_REDIS_CLUSTER
  };

  const handleClear = () => {
    Object.assign(formData, {
      use: '',
      method: '',
      complexity: '',
    });
  };
</script>

<style lang="less" scoped>
  .recommend-architecture-form {
    background: #f5f7fa;
    padding: 12px 16px;

    :deep(.bk-form-label) {
      font-size: 12px;
      font-weight: 700;
    }

    :deep(.bk-radio-group) {
      flex-direction: column;
    }

    :deep(.bk-radio) {
      margin-left: 0;
    }

    :deep(.bk-radio-label) {
      font-size: 12px;
    }

    .recommend-architecture {
      font-size: 12px;
      margin-bottom: 8px;
      display: flex;

      .recommend-architecture-item {
        .item-text {
          font-weight: 700;
        }
        // &:not(:first-child) {
        //   margin-top: 8px;
        // }
      }
    }
  }
</style>
