import DbUpload from './Index.vue';

export default DbUpload;

export type {
  DbUploadOptions,
  DuplicateChecker,
  ListPosition,
  MaxSize,
  UploadFile,
  UploadMode,
  UploadRawFile,
} from './types';
export { UploadStatus } from './types';
export type { XhrUploadOptions } from './utils/index';
export type { ParseExcelOptions } from './utils/index';
export {
  BKREPO_DEFAULT_HEADERS,
  createBkrepoUploadUrl,
  createXhrUpload,
  formatFileSize,
  getMaxSize,
  parseExcelFile,
  parseXhrResponse,
  validateAccept,
  validateSize,
} from './utils/index';
