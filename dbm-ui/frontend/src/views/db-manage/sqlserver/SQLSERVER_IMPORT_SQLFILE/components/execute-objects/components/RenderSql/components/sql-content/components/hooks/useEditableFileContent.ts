import { computed, type Ref, ref, shallowRef, watch } from 'vue';

import GrammarCheckModel from '@services/model/sql-import/grammar-check';
import { getFileContent } from '@services/source/storage';

import { useSqlImport } from '@stores';

import SqlFileModel from '@views/db-manage/common/model/sql-file/SqlFile';

import { getSQLFilename } from '@utils';

export default (modelValue: Ref<string[]>) => {
  const { uploadFilePath } = useSqlImport();

  const selectFileName = ref('');
  const isContentLoading = ref(false);
  const fileNameList = shallowRef<Array<string>>([]);
  const fileDataMap = ref<Record<string, SqlFileModel>>({});

  // 当前选择文件数据
  const selectFileData = computed(() => fileDataMap.value[selectFileName.value]);

  const fetchFileContentByFileName = (fileName: string) => {
    if (!uploadFilePath) {
      return;
    }
    isContentLoading.value = true;
    getFileContent({
      file_path: `${uploadFilePath}/${fileName}`,
    })
      .then((data) => {
        const sqlFileName = getSQLFilename(fileName);
        const fileInfo = fileDataMap.value[sqlFileName];
        if (fileInfo) {
          fileDataMap.value[sqlFileName].content = data.content;
        }
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
        fileDataMap.value[selectFileName.value].state === SqlFileModel.CHECKING
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
    fileDataMap.value = localFileNameList.reduce<{ [fileName: string]: SqlFileModel }>((result, localFileName) => {
      const sqlFile = new SqlFileModel({
        realFilePath: filePathMap[localFileName],
      });
      sqlFile.grammarCheckStart();
      sqlFile.grammarCheckSuccessed({
        [filePathMap[localFileName]]: new GrammarCheckModel(),
      });
      return Object.assign(result, { [localFileName]: sqlFile });
    }, {});
  };

  return {
    fetchFileContentByFileName,
    fileDataMap,
    fileNameList,
    initEditableFile,
    isContentLoading,
    selectFileData,
    selectFileName,
  };
};
