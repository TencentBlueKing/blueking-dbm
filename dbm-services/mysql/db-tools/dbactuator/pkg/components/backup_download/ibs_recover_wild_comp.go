package backup_download

import (
	"path/filepath"
	"regexp"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/jinzhu/copier"
	"github.com/pkg/errors"
)

func (c *IBSRecoverComp) skipFilesAndInit() error {
	taskFilesExist := []string{}
	for i, tf := range c.Params.TaskFiles {
		if tf.TaskId != "" {
			if tf.FileName != "" && tf.Size != "" {
				f := filepath.Join(c.Params.Directory, tf.FileName)
				if skip, err := c.skipFileExists(f, tf.Size); err != nil {
					return err
				} else if skip {
					taskFilesExist = append(taskFilesExist, tf.FileName)
					continue
				}
			}
			c.Params.taskIdSlice = append(c.Params.taskIdSlice, tf.TaskId)
		} else if tf.FileName != "" {
			// 如果只提供的 file_name，必然要去查备份系统
			// 如果提供了 file_name 和 size，当本地 size 和提供的 size 不相同时，才需要查询备份系统。
			// 查完备份系统，才知道是否 skip，所以这里 SkipFileExists 有 2 次
			f := filepath.Join(c.Params.Directory, tf.FileName)
			if skip, err := c.skipFileExists(f, tf.Size); err != nil {
				return err
			} else if skip {
				taskFilesExist = append(taskFilesExist, tf.FileName)
				continue
			} // 文件名本地不存在，或者存在但大小不一致 已删除，根据文件名去获取 task_id

			// query task_id with file_name
			ibsQuery := &IBSQueryParam{
				IBSInfo: c.Params.IBSInfo,
				client:  c.Params.client,
			}
			copier.Copy(&ibsQuery.IBSQueryReq, &c.Params.IBSQuery)
			ibsQuery.IBSQueryReq.FileName = tf.FileName
			logger.Info("request IBS to get task_id,file size, params: %+v", ibsQuery)
			queryResp, err := ibsQuery.BsQuery(ibsQuery.IBSQueryReq)
			if err != nil {
				return err
			} else if queryResp.Num != 1 {
				return errors.Errorf(
					"expect 1 task_id but got %d %+v. requst params:%+v",
					queryResp.Num, queryResp, ibsQuery.IBSQueryReq,
				)
			}
			task := queryResp.Detail[0]
			if task.FileName != tf.FileName {
				return errors.Errorf("file_name %s is not the same as remote %s", tf.FileName, task.FileName)
			} else if skip, err := c.skipFileExists(f, task.Size); err != nil {
				return err
			} else if skip {
				taskFilesExist = append(taskFilesExist, tf.FileName)
				copier.Copy(&tf, &task)
				c.Params.TaskFiles[i] = tf // 也要更新下需要下载的对象，后面 PostCheck 会用到(size)
				continue
			}
			copier.Copy(&tf, &task)
			c.Params.TaskFiles[i] = tf
			if task.Status != BACKUP_TASK_SUCC {
				// todo 这里最好给个选项，部分文件异常，是否继续下载其它文件
				return errors.Errorf("file abnormal status=%s %s", task.Status, task.FileName)
			}
			c.Params.taskIdSlice = append(c.Params.taskIdSlice, task.TaskId)
		} else {
			return errors.New("task_id and file_name cannot be empty both")
		}
	}
	logger.Info("files already exists and skip download: %+v", taskFilesExist)
	if c.Params.IBSRecoverReq.TaskidList != "" {
		taskIdList := util.SplitAnyRuneTrim(c.Params.IBSRecoverReq.TaskidList, ",")
		c.Params.taskIdSlice = append(c.Params.taskIdSlice, taskIdList...)
		c.Params.taskIdSlice = util.UniqueStrings(c.Params.taskIdSlice)
	}
	c.Params.IBSRecoverReq.TaskidList = strings.Join(c.Params.taskIdSlice, ",")
	logger.Info("params for recover: %+v", c.Params)
	return nil
}

// skipFilesAndInitWild 会把 task_files_wild 里找到的文件，初始化到 task_files
// 外面应该再次调用 skipFilesAndInit 来判断需要下载的文件
func (c *IBSRecoverComp) skipFilesAndInitWild() error {
	wild := c.Params.TaskFilesWild
	ibsQuery := &IBSQueryParam{
		IBSInfo: c.Params.IBSInfo,
		client:  c.Params.client,
	}
	copier.Copy(&ibsQuery.IBSQueryReq, &c.Params.IBSQuery)
	ibsQuery.IBSQueryReq.FileName = wild.NameSearch
	logger.Info("request IBS to get task_id,file size, params: %+v", ibsQuery)
	queryResp, err := ibsQuery.BsQuery(ibsQuery.IBSQueryReq)
	if err != nil {
		return err
	}
	/*
		dbport := 3306
		// binlogXX.xxx  binlog.xxx binlog文件名里如果port=3306 是不带端口
		regBinlog := regexp.MustCompile(fmt.Sprintf(`^.+%d\.\d+(\..*)*$`, dbport))
		// (app)_(host)_(ip)_(port)_(date)_(time).XXX (app)_(host)_(ip)_(port)_(date)_(time)_xtra.XXX  全备文件里，一定会带port
		regFullFile := regexp.MustCompile(fmt.Sprintf(`.+_.+_.+_%d_\d+_\d+.+`, dbport))
		regFullNonData := regexp.MustCompile(`.*(\.priv|\.info)`)
	*/
	reg := regexp.MustCompile(wild.NameRegex)
	for _, task := range queryResp.Detail {
		if wild.NameRegex != "" {
			if !reg.MatchString(task.FileName) {
				logger.Info("file %s not match file_name_regex", task.FileName)
				continue
			}
			if wild.FileTag != "" && wild.FileTag != task.FileTag {
				logger.Info("file %s %s not match file_tag %s", task.FileName, task.FileTag, wild.FileTag)
				continue
			}
			taskFile := TaskFilesExact{}
			copier.Copy(&taskFile, &task)
			c.Params.TaskFiles = append(c.Params.TaskFiles, taskFile)
		}
	}
	return nil
}
