<template>
  <div>
    <div style="width: 500px; margin: 200px auto">
      <QuickSearch
        :data="data"
        @change="handleChange" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';

  import QuickSearch, { type Props } from '@components/db-quick-serach/bk-quick-search/Index.vue';

  const data: Props['data'] = [
    {
      description: '测试一发',
      id: 'id',
      name: 'ID',
    },
    {
      id: 'name',
      list: [
        {
          label: '张三',
          value: 'zhangsan',
        },
        {
          label: '李四',
          value: ' list',
        },
      ],
      name: '多选',
      type: 'multiple',
    },
    {
      id: 'sex',
      list: [
        {
          label: '男',
          value: ' body',
        },
        {
          label: '女',
          value: ' girl',
        },
      ],
      name: '单选',
      type: 'single',
    },
    {
      id: 'sehg',
      list: [
        {
          label: '广东',
          value: ' 广东',
        },
        {
          label: '广西',
          value: ' 广西',
        },
        {
          label: '湖南',
          value: ' 湖南',
        },
        {
          label: '湖北',
          value: ' 湖北',
        },
        {
          label: '四川',
          value: ' 四川',
        },
      ],
      name: '自定义',
      type: 'single',
    },
    {
      id: 'sehgasd',
      list: [
        {
          children: [
            {
              label: '一年级',
              value: '一年级',
            },
            {
              label: '二年级',
              value: '二年级',
            },
            {
              label: '三年级',
              value: '三年级',
            },
            {
              label: '四年级',
              value: '四年级',
            },
            {
              label: '五年级',
              value: '五年级',
            },
            {
              label: '六年级',
              value: '六年级',
            },
          ],
          label: ' 小学',
          value: '小学',
        },
        {
          children: [
            {
              label: '一年级',
              value: '一年级',
            },
            {
              label: '二年级',
              value: '二年级',
            },
            {
              label: '三年级',
              value: '三年级',
            },
          ],
          label: ' 初中',
          value: '初中',
        },
        {
          children: [
            {
              label: '一年级',
              value: '一年级',
            },
            {
              label: '二年级',
              value: '二年级',
            },
            {
              label: '三年级',
              value: '三年级',
            },
          ],
          label: ' 高中',
          value: '高中',
        },
      ],
      name: '级联',
      type: 'cascader',
    },
    {
      id: 'multiple-cascader',
      list: [
        {
          children: [
            {
              label: '小学一年级',
              value: '小学一年级',
            },
            {
              label: '小学二年级',
              value: '小学二年级',
            },
            {
              label: '小学三年级',
              value: '小学三年级',
            },
            {
              label: '小学四年级',
              value: '小学四年级',
            },
            {
              label: '小学五年级',
              value: '小学五年级',
            },
            {
              label: '小学六年级',
              value: '小学六年级',
            },
          ],
          label: ' 小学',
          value: '小学',
        },
        {
          children: [
            {
              label: '初中一年级',
              value: '初中一年级',
            },
            {
              label: '初中二年级',
              value: '初中二年级',
            },
            {
              label: '初中三年级',
              value: '初中三年级',
            },
          ],
          label: ' 初中',
          value: '初中',
        },
        {
          children: [
            {
              label: '高中一年级',
              value: '高中一年级',
            },
            {
              label: '高中二年级',
              value: '高中二年级',
            },
            {
              label: '高中三年级',
              value: '高中三年级',
            },
          ],
          label: ' 高中',
          value: '高中',
        },
      ],
      name: '级联多选',
      type: 'multiple-cascader',
    },
    {
      id: 'date',
      name: '日期',
      type: 'date',
    },
    {
      id: 'date-range',
      name: '日期范围',
      props: {
        presets: {
          今天: [dayjs().toDate(), dayjs().toDate()],
          最近3天: [dayjs().subtract(2, 'day').toDate(), dayjs().toDate()],
          最近7天: [dayjs().subtract(6, 'day').toDate(), dayjs().toDate()],
        },
      },
      type: 'date-range',
    },
    {
      id: 'datetime',
      name: '日期时间',
      type: 'datetime',
    },
    {
      id: 'datetime-range',
      name: '日期时间范围',
      type: 'datetime-range',
    },
  ];

  const handleChange = (payload: any) => {
    console.log('serach select change = ', payload);
  };
</script>
