import {
  onBeforeUnmount,
} from 'vue';

export default () => {
  const handleKeydown = (event: KeyboardEvent) => {
    console.log(event);
  };

  document.body.addEventListener('keydown', handleKeydown);

  onBeforeUnmount(() => {
    document.body.removeEventListener('keydown', handleKeydown);
  });
};
