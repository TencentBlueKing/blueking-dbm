import { onMounted, ref, watch } from 'vue';

export default {
  name: 'render-avatar',
  props: ['user', 'urlMethod'],
  setup(props: any) {
    const avatar = ref('');
    onMounted(async () => {
      try {
        if (typeof props.user === 'string') {
          avatar.value = await props.urlMethod(props.user);
        } else if (typeof props.user === 'object') {
          avatar.value = props.user.avatar || props.user.logo || (await props.urlMethod(props.user.username));
        }
      } catch (e) {
        console.error(e);
      }
    });

    const userSelectorAvatarRef = ref(null);

    watch(avatar, (v: string) => {
      if (v) {
        userSelectorAvatarRef.value.style.backgroundImage = `url(${avatar.value})`;
      }
    });

    return () => <span ref={userSelectorAvatarRef} class="user-selector-avatar"></span>;
  },
};
