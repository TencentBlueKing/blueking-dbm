// Package jobmanager 原子任务工厂类 与 管理类
package jobmanager

import (
	"dbm-services/mongo/db-tools/dbactuator/pkg/atomjobs/atommongodb"
	"dbm-services/mongo/db-tools/dbactuator/pkg/atomjobs/atomsys"
	"fmt"
	"slices"
	"log"
	"runtime/debug"
	"strings"
	"sync"
	"time"
	"dbm-services/mongo/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongo/db-tools/dbactuator/pkg/util"
)

// AtomJobCreatorFunc 原子任务创建接口
type AtomJobCreatorFunc func() jobruntime.JobRunner

// JobGenericManager 原子任务管理者
type JobGenericManager struct {
	Runners       []jobruntime.JobRunner `json:"runners"`
	atomJobMapper map[string]AtomJobCreatorFunc
	once          sync.Once
	runtime       *jobruntime.JobGenericRuntime
}

// NewJobGenericManager new
func NewJobGenericManager(uid, rootID, nodeID, versionID, payload, payloadFormat, atomJobs, baseDir string) (
	ret *JobGenericManager, err error) {
	runtime, err := jobruntime.NewJobGenericRuntime(uid, rootID, nodeID, versionID,
		payload, payloadFormat, atomJobs, baseDir)
	if err != nil {
		log.Panicf(err.Error())
	}
	ret = &JobGenericManager{
		runtime: runtime,
	}
	return
}

// LoadAtomJobs 加载子任务
func (m *JobGenericManager) LoadAtomJobs() (err error) {
	defer func() {
		// err最后输出到标准错误
		if err != nil {
			m.runtime.PrintToStderr(err.Error())
		}
	}()
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("%s", (debug.Stack()))
		}
	}()
	m.runtime.AtomJobList = strings.TrimSpace(m.runtime.AtomJobList)
	if m.runtime.AtomJobList == "" {
		err = fmt.Errorf("atomJobList(%s) cannot be empty", m.runtime.AtomJobList)
		m.runtime.Logger.Error(err.Error())
		return
	}
	jobList := strings.Split(m.runtime.AtomJobList, ",")
	for _, atomName := range jobList {
		atomName = strings.TrimSpace(atomName)
		if atomName == "" {
			continue
		}
		atom := m.GetAtomJobInstance(atomName)
		if atom == nil {
			err = fmt.Errorf("atomJob(%s) not found", atomName)
			m.runtime.Logger.Error(err.Error())
			return
		}
		m.Runners = append(m.Runners, atom)
		m.runtime.Logger.Info(fmt.Sprintf("atomJob:%s instance load success", atomName))
	}
	return
}

// RunAtomJobs 顺序执行原子任务
func (m *JobGenericManager) RunAtomJobs() (err error) {
	defer func() {
		// err最后输出到标准错误
		if err != nil {
			m.runtime.PrintToStderr(err.Error() + "\n")
		}
	}()
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("%s", string(debug.Stack()))
		}
	}()

	m.runtime.StartHeartbeat(10 * time.Second)

	defer m.runtime.StopHeartbeat()

	for _, runner := range m.Runners {
		name := util.GetTypeName(runner)
		m.runtime.Logger.Info(fmt.Sprintf("begin to run %s init", name))
		if err = runner.Init(m.runtime); err != nil {
			return
		}
		m.runtime.Logger.Info(fmt.Sprintf("begin to run %s", name))
		err = runner.Run()
		if err != nil {
			m.runtime.Logger.Info(fmt.Sprintf("runner %s run failed,err:%s", name, err))
			return
		}
		m.runtime.Logger.Info(fmt.Sprintf("finished run %s", name))
	}
	m.runtime.Logger.Info(fmt.Sprintf("run all atomJobList:%s success", m.runtime.AtomJobList))

	m.runtime.OutputPipeContextData()
	return
}

// RegisterAtomJob 注册原子任务
func (m *JobGenericManager) RegisterAtomJob() {
	m.once.Do(func() {
		m.atomJobMapper = make(map[string]AtomJobCreatorFunc)
		for _, f := range []AtomJobCreatorFunc{
			atomsys.NewOsMongoInit,
			atommongodb.NewMongoDBInstall,
			atommongodb.NewMongoSInstall,
			atommongodb.NewInitiateReplicaset,
			atommongodb.NewAddShardToCluster,
			atommongodb.NewAddUser,
			atommongodb.NewDelUser,
			atommongodb.NewMongoDReplace,
			atommongodb.NewMongoRestart,
			atommongodb.NewStepDown,
			atommongodb.NewBalancer,
			atommongodb.NewDeInstall,
			atommongodb.NewExecScript,
			atommongodb.NewSetProfiler,
			atommongodb.NewMongoDChangeOplogSize,
			atommongodb.NewBackupJob,
			atommongodb.NewRestoreJob,
			atommongodb.NewPitrRecoverJob,
			atommongodb.NewRemoveNsJob,
		} {
			m.atomJobMapper[f().Name()] = f
		}
	})
}

// GetJobNameList 获取原子任务名字列表
func (m *JobGenericManager) GetJobNameList() []string {
	var ret []string
	for name := range m.atomJobMapper {
		ret = append(ret, name)
	}
	slices.Sort(ret)
	return ret
}

// GetAtomJobInstance 根据atomJobName,从m.atomJobMapper中获取其creator函数,执行creator函数
func (m *JobGenericManager) GetAtomJobInstance(atomJob string) jobruntime.JobRunner {
	m.RegisterAtomJob()
	creator, ok := m.atomJobMapper[strings.ToLower(atomJob)]
	if ok {
		return creator()
	}
	return nil
}
