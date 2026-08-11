<template>
  <template v-if="groups.length">
    <template v-if="all">
      <div
        v-for="group in groups"
        :key="group.machineType"
        class="machine-spec-cell-group">
        <div
          v-for="(spec, specIndex) in group.specs"
          :key="specIndex"
          class="machine-spec-cell-line">
          <span class="machine-spec-cell-role">{{ group.roleName }}</span>
          <span>：</span>
          <MachineSpecItem :spec="spec" />
        </div>
      </div>
    </template>
    <template v-else>
      <div
        v-for="(item, index) in displayList"
        :key="`${item.machineType}-${item.spec.spec_name}`"
        class="machine-spec-cell-line">
        <span class="machine-spec-cell-role">{{ item.roleName }}</span>
        <span>：</span>
        <MachineSpecItem :spec="item.spec" />
        <BkPopover
          v-if="index === displayList.length - 1 && flatList.length > MAX_DISPLAY"
          ext-cls="machine-spec-cell-popover-wrapper"
          theme="light"
          trigger="click">
          <span class="machine-spec-cell-more">({{ t('共 n 个', [flatList.length]) }})</span>
          <template #content>
            <div class="machine-spec-cell-popover">
              <div class="popover-header">{{ t('共 n 个', [flatList.length]) }}</div>
              <div
                v-for="g in groups"
                :key="g.machineType">
                <div
                  v-for="(spec, specIndex) in g.specs"
                  :key="specIndex"
                  class="popover-line">
                  <span class="popover-role">{{ g.roleName }}</span>
                  <span class="popover-colon">：</span>
                  <MachineSpecItem :spec="spec" />
                </div>
              </div>
            </div>
          </template>
        </BkPopover>
      </div>
    </template>
  </template>
  <span v-else>--</span>
</template>

<script setup lang="ts">
  import BkPopover from 'bkui-vue/lib/popover';
  import { useI18n } from 'vue-i18n';

  import type { MachineSpec } from '@services/types';

  import { groupMachineSpecs } from '@views/db-manage/common/machineSpecs';

  import MachineSpecItem from '../machine-spec-item/Index.vue';

  interface Props {
    all?: boolean;
    specs: MachineSpec[];
  }

  const props = withDefaults(defineProps<Props>(), {
    all: false,
  });

  const { t } = useI18n();

  /** 列表场景最多展示的规格记录条数 */
  const MAX_DISPLAY = 2;

  const groups = computed(() => groupMachineSpecs(props.specs || []));

  /** 按「角色 → 规格」双层循环展平为有序列表 */
  const flatList = computed(() => groups.value.flatMap((group) => group.specs.map((spec) => ({ ...group, spec }))));

  /** 列表场景仅展示前 2 条规格记录 */
  const displayList = computed(() => (props.all ? [] : flatList.value.slice(0, MAX_DISPLAY)));
</script>
<style lang="less">
  .machine-spec-cell-line {
    white-space: nowrap;
  }

  .machine-spec-cell-role {
    font-weight: 600;
    color: #313238;
  }

  .machine-spec-cell-more {
    margin-left: 4px;
    color: #3a84ff;
    cursor: pointer;
  }

  .machine-spec-cell-popover-wrapper {
    .popover-line {
      line-height: 22px;
    }

    .popover-role {
      color: #313238;
    }
  }

  .machine-spec-cell-popover {
    .popover-header {
      padding-bottom: 4px;
      font-size: 14px;
      font-weight: bolder;
      color: #313238;
      // border-bottom: 1px solid #dcdee5;
    }

    // .popover-line {
    //   padding-top: 6px;
    // }
  }
</style>
