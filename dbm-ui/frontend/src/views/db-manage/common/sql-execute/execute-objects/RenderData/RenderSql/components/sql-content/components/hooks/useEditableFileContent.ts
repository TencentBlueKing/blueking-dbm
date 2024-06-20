import { computed, type Ref, ref, shallowRef, watch } from 'vue';

import GrammarCheckModel from '@services/model/sql-import/grammar-check';
import { getFileContent } from '@services/source/storage';

import { useSqlImport } from '@stores';

import { getSQLFilename } from '@utils';

import { createFileData, type IFileData } from '../RenderFileList.vue';

export default (modelValue: Ref<string[]>) => {
  const { uploadFilePath } = useSqlImport();

  const selectFileName = ref('');
  const isContentLoading = ref(false);
  const fileNameList = shallowRef<Array<string>>([]);
  const fileDataMap = ref<Record<string, IFileData>>({});

  // 当前选择文件数据
  const selectFileData = computed(() => fileDataMap.value[selectFileName.value]);

  const fetchFileContentByFileName = (fileName: string) => {
    if (!uploadFilePath) {
      return;
    }
    isContentLoading.value = true;
    const latestfileDataMap = { ...fileDataMap.value };
    getFileContent({
      file_path: `${uploadFilePath}/${fileName}`,
    })
      .then((data) => {
        latestfileDataMap[getSQLFilename(fileName)].content = data.content;
        fileDataMap.value = latestfileDataMap;
      })
      .finally(() => {
        isContentLoading.value = false;
      });
  };

  watch(
    selectFileName,
    () => {
      // 编辑状态不需要 SQL 文件检测，需要异步获取文件内容
      if (
        !selectFileName.value ||
        fileDataMap.value[selectFileName.value].content ||
        fileDataMap.value[selectFileName.value].isUploading ||
        !fileDataMap.value[selectFileName.value].grammarCheck
      ) {
        return;
      }

      fetchFileContentByFileName(fileDataMap.value[selectFileName.value].realFilePath);
    },
    {
      immediate: true,
    },
  );

  const initEditableFile = () => {
    const localFileNameList = [] as string[];
    const filePathMap = {} as Record<string, string>;

    modelValue.value.forEach((filePath: string) => {
      // 本地 SQL 文件上传后会拼接随机数前缀，需要解析正确的文件名
      const localFileName = getSQLFilename(filePath);
      localFileNameList.push(localFileName);
      filePathMap[localFileName] = filePath;
    });

    fileNameList.value = localFileNameList;
    fileDataMap.value = localFileNameList.reduce(
      (result, localFileName) => ({
        ...result,
        [localFileName]: createFileData({
          isSuccess: true,
          isCheckFailded: false,
          realFilePath: filePathMap[localFileName],
          grammarCheck: new GrammarCheckModel(),
        }),
      }),
      {} as Record<string, IFileData>,
    );
  };

  return {
    isContentLoading,
    selectFileName,
    selectFileData,
    fileNameList,
    fileDataMap,
    initEditableFile,
    fetchFileContentByFileName,
  };
};
