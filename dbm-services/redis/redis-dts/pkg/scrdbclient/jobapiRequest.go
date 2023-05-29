// Package scrdbclient 封装jobapi相关请求,包括执行脚本,传输文件,查看状态等
package scrdbclient

import (
	"encoding/json"
	"fmt"
	"net/http"
	"path/filepath"
	"time"

	"dbm-services/redis/db-tools/dbmon/util"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/remoteOperation"
)

// FastExecuteScript 快速执行脚本
func (c *Client) FastExecuteScript(param FastExecScriptReq) (ret FastExecScriptResp, err error) {
	result, err := c.Do(http.MethodPost, constvar.DbmJobApiFastExecuteScriptURL, param)
	if err != nil {
		return
	}
	err = json.Unmarshal(result.Data, &ret)
	if err != nil {
		err = fmt.Errorf("FastExecuteScript unmarshal data fail,err:%v,result.Data:%s", err, string(result.Data))
		c.logger.Error(err.Error())
		return
	}
	return
}

// GetJobInstanceStatus 获取job实例状态
func (c *Client) GetJobInstanceStatus(param GetJobInstanceStatusReq) (ret GetJobInstanceStatusResp, err error) {
	result, err := c.Do(http.MethodPost, constvar.DbmJobApiGetJobInstanceStatusURL, param)
	if err != nil {
		return
	}
	err = json.Unmarshal(result.Data, &ret)
	if err != nil {
		err = fmt.Errorf("GetJobInstanceStatus unmarshal data fail,err:%v,result.Data:%s", err, string(result.Data))
		c.logger.Error(err.Error())
		return
	}
	return
}

// BatchGetJobInstanceIpLog 获取job实例ip日志
func (c *Client) BatchGetJobInstanceIpLog(param BatchGetJobInstanceIpLogReq) (
	ret BatchGetJobInstanceIpLogResp, err error,
) {
	result, err := c.Do(http.MethodPost, constvar.DbmJobApiBatchGetJobInstanceIPLogURL, param)
	if err != nil {
		return
	}
	err = json.Unmarshal(result.Data, &ret)
	if err != nil {
		err = fmt.Errorf("BatchGetJobInstanceIpLog unmarshal data fail,err:%v,result.Data:%s", err, string(result.Data))
		c.logger.Error(err.Error())
		return
	}
	return
}

// FastTransferFile 快速传输文件
func (c *Client) FastTransferFile(param TransferFileReq) (ret FastExecScriptResp, err error) {
	result, err := c.Do(http.MethodPost, constvar.DbmJobApiTransferFileURL, param)
	if err != nil {
		return
	}
	err = json.Unmarshal(result.Data, &ret)
	if err != nil {
		err = fmt.Errorf("FastTransferFile unmarshal data fail,err:%v,result.Data:%s", err, string(result.Data))
		c.logger.Error(err.Error())
		return
	}
	return
}

// ExecNew 执行脚本并等待结果
func (c *Client) ExecNew(param FastExecScriptReq, maxRetryTimes int) (retList []BatchScriptLogItem, err error) {
	var isLocalCmd bool
	isLocalCmd, err = param.IsLocalScript()
	if err != nil {
		return
	}
	if isLocalCmd && param.ScriptLanguage == 1 {
		cmdRet, err := util.RunBashCmd(param.ScriptContent, "", nil, time.Duration(param.Timeout)*time.Second)
		if err != nil {
			return retList, err
		}
		retList = append(retList, BatchScriptLogItem{
			IPItem:     param.IPList[0],
			LogContent: cmdRet,
		})
		return retList, nil
	}
	ret := BatchGetJobInstanceIpLogResp{}
	if constvar.IsGlobalEnv() {
		return c.ExecBySshNew(param, maxRetryTimes)
	}
	msg := fmt.Sprintf("starting exec command,params:%s", util.ToString(param))
	c.logger.Info(msg)

	if maxRetryTimes <= 0 {
		maxRetryTimes = 1
	}
	var execRet FastExecScriptResp
	var i int
	for i = 0; i < maxRetryTimes; i++ {
		execRet, err = c.FastExecuteScript(param)
		if err != nil {
			time.Sleep(2 * time.Second)
			continue
		}
		break
	}
	if i >= maxRetryTimes && err != nil {
		// 如果调用Job平台api失败,通过ssh方式继续执行
		c.logger.Info("FastExecuteScript api fail,try to use ssh to exec command")
		return c.ExecBySshNew(param, maxRetryTimes)
	}
	msg = fmt.Sprintf("GetJobInstanceStatus job_instance_id:%d", execRet.JobInstanceID)
	c.logger.Info(msg)

	statusReq := GetJobInstanceStatusReq{}
	statusReq.JobInstanceID = execRet.JobInstanceID
	statusReq.StepInstanceID = execRet.StepInstanceID

	var statusResp GetJobInstanceStatusResp
	var times int = 0
	i = 0
	for {
		statusResp, err = c.GetJobInstanceStatus(statusReq)
		if err != nil {
			times++
			err = fmt.Errorf("GetJobInstanceStatus fail,err:%v,job_instance_id:%d,step_instance_id:%d",
				err, execRet.JobInstanceID, execRet.StepInstanceID)
			if times >= maxRetryTimes {
				c.logger.Error("Finally ..." + err.Error())
				return retList, err
			} else {
				c.logger.Warn("Retry... " + err.Error())
				time.Sleep(2 * time.Second)
				continue
			}
		}
		if statusResp.JobInstance.Status >= 3 {
			break
		}
		time.Sleep(2 * time.Second)
		i++
		if i%30 == 0 {
			// 每分钟打印一次进度日志
			c.logger.Info(fmt.Sprintf("ExecNew job_instance_id:%d,step_instance_id:%d still running,status:%d",
				execRet.JobInstanceID, execRet.StepInstanceID, statusResp.JobInstance.Status))
		}
	}
	if statusResp.JobInstance.Status != 3 {
		err = fmt.Errorf("GetJobInstanceStatus fail,job_instance_id:%d,step_instance_id:%d,status:%d",
			execRet.JobInstanceID, execRet.StepInstanceID, statusResp.JobInstance.Status)
		c.logger.Error(err.Error())
		return retList, err
	}
	c.logger.Info(fmt.Sprintf("ExecNew job_instance_id:%d,step_instance_id:%d success,status:%d",
		statusReq.JobInstanceID, statusReq.StepInstanceID, statusResp.JobInstance.Status))

	logReq := BatchGetJobInstanceIpLogReq{}
	logReq.JobInstanceID = execRet.JobInstanceID
	logReq.StepInstanceID = execRet.StepInstanceID
	logReq.IPList = param.IPList
	for i := 0; i < maxRetryTimes; i++ {
		if i >= maxRetryTimes {
			return retList, err
		}
		ret, err = c.BatchGetJobInstanceIpLog(logReq)
		if err != nil {
			time.Sleep(2 * time.Second)
			continue
		}
		break
	}
	return ret.ToBatchScriptLogList(), nil
}

// SendNew 文件传输并等待结果
func (c *Client) SendNew(param TransferFileReq, maxRetryTimes int) (err error) {
	msg := fmt.Sprintf("starting send file,params:%s", util.ToString(param))
	c.logger.Info(msg)

	if maxRetryTimes <= 0 {
		maxRetryTimes = 1
	}
	var execRet FastExecScriptResp
	var i int
	for i = 0; i < maxRetryTimes; i++ {
		execRet, err = c.FastTransferFile(param)
		if err != nil {
			time.Sleep(2 * time.Second)
			continue
		}
		break
	}
	if i >= maxRetryTimes && err != nil {
		// 如果调用Job平台api失败,通过ssh方式继续执行
		c.logger.Info("FastTransferFile api fail,try to use ssh to download file")
		return c.DownloadFileToLocalBySSH(param, maxRetryTimes)
	}
	c.logger.Info(fmt.Sprintf("FastTransferFile api success,ret:%s", util.ToString(execRet)))

	msg = fmt.Sprintf("GetJobInstanceStatus job_instance_id:%d", execRet.JobInstanceID)
	c.logger.Info(msg)

	statusReq := GetJobInstanceStatusReq{}
	statusReq.JobInstanceID = execRet.JobInstanceID
	statusReq.StepInstanceID = execRet.StepInstanceID

	var statusResp GetJobInstanceStatusResp
	var times int = 0
	i = 0
	for {
		statusResp, err = c.GetJobInstanceStatus(statusReq)
		if err != nil {
			times++
			err = fmt.Errorf("GetJobInstanceStatus fail,err:%v,job_instance_id:%d,step_instance_id:%d",
				err, execRet.JobInstanceID, execRet.StepInstanceID)
			if times >= maxRetryTimes {
				c.logger.Error("Finally ..." + err.Error())
				return err
			} else {
				c.logger.Warn("Retry... " + err.Error())
				time.Sleep(2 * time.Second)
				continue
			}
		}
		if statusResp.JobInstance.Status >= 3 {
			break
		}
		time.Sleep(2 * time.Second)
		i++
		if i%30 == 0 {
			// 每分钟打印一次进度日志
			c.logger.Info(fmt.Sprintf("GetJobInstanceStatus job_instance_id:%d,step_instance_id:%d still running,status:%d",
				execRet.JobInstanceID, execRet.StepInstanceID, statusResp.JobInstance.Status))
		}
	}
	if statusResp.JobInstance.Status != 3 {
		err = fmt.Errorf("GetJobInstanceStatus fail,job_instance_id:%d,step_instance_id:%d,status:%d",
			statusReq.JobInstanceID, statusReq.StepInstanceID, statusResp.JobInstance.Status)
		c.logger.Error(err.Error())
		return err
	}
	c.logger.Info(fmt.Sprintf("SendNew job_instance_id:%d,step_instance_id:%d success,status:%d",
		statusReq.JobInstanceID, statusReq.StepInstanceID, statusResp.JobInstance.Status))
	return nil
}

// ExecBySshNew 通过ssh执行脚本并等待结果
func (c *Client) ExecBySshNew(param FastExecScriptReq, maxRetryTimes int) (retList []BatchScriptLogItem, err error) {
	var isLocalCmd bool
	isLocalCmd, err = param.IsLocalScript()
	if err != nil {
		return
	}
	if isLocalCmd && param.ScriptLanguage == 1 {
		cmdRet, err := util.RunBashCmd(param.ScriptContent, "", nil, time.Duration(param.Timeout)*time.Second)
		if err != nil {
			return retList, err
		}
		retList = append(retList, BatchScriptLogItem{
			IPItem:     param.IPList[0],
			LogContent: cmdRet,
		})
		return retList, nil
	}
	for _, ip := range param.IPList {
		sshCli, err := remoteOperation.NewISshClientByEnvAbsVars(ip.IP, c.logger)
		if err != nil {
			c.logger.Error(err.Error())
			return retList, err
		}
		bashRet, err := sshCli.RemoteBash(param.ScriptContent)
		if err != nil {
			c.logger.Error(err.Error())
			return retList, err
		}
		retList = append(retList, BatchScriptLogItem{
			IPItem:     ip,
			LogContent: bashRet,
		})
	}
	return retList, nil
}

// DownloadFileToLocalBySSH 如果目标机器是本机,则通过ssh下载文件
func (c *Client) DownloadFileToLocalBySSH(param TransferFileReq, maxRetryTimes int) (err error) {
	isLocalCopy, err := param.IsLocalCopy()
	if err != nil {
		return
	}
	if isLocalCopy {
		for _, sitem := range param.SourceList {
			for _, file := range sitem.FileList {
				cpCmd := fmt.Sprintf("cp -r %s %s", file, param.TargetDir)
				c.logger.Info(cpCmd)
				_, err = util.RunBashCmd(cpCmd, "", nil, 30*time.Minute)
				if err != nil {
					return nil
				}
			}
		}
	}

	isLocalTarget, err := param.IsLocalTarget()
	if err != nil {
		return
	}
	if !isLocalTarget {
		err = fmt.Errorf("target not local,targetData:%s", util.ToString(param.TargetIPList))
		c.logger.Error(err.Error())
		return err
	}

	for _, sitem := range param.SourceList {
		sshCli, err := remoteOperation.NewISshClientByEnvAbsVars(sitem.IP, c.logger)
		if err != nil {
			c.logger.Error(err.Error())
			return err
		}
		for _, file := range sitem.FileList {
			err = sshCli.RemoteDownload(filepath.Dir(file), param.TargetDir, filepath.Base(file), 400)
			if err != nil {
				c.logger.Error(err.Error())
				return err
			}
		}
	}
	return
}
