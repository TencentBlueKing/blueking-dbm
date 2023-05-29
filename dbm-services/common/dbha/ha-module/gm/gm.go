// Package gm TODO
package gm

import (
	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/util"
	"time"
)

// InstanceKey instance key info
type InstanceKey struct {
	Ip   string
	Port int
}

// DoubleCheckInstanceInfo double check instance info
type DoubleCheckInstanceInfo struct {
	AgentIp      string
	AgentPort    int
	db           dbutil.DataBaseDetect
	ReceivedTime time.Time
	ConfirmTime  time.Time
	ResultInfo   string
}

// ModuleReportInfo module info
type ModuleReportInfo struct {
	Module string
}

// HAReporter ha reporter
type HAReporter struct {
	gm             *GM
	lastReportTime time.Time
}

// GM work struct
type GM struct {
	gdm            *GDM
	gmm            *GMM
	gqa            *GQA
	gcm            *GCM
	HaDBClient     *client.HaDBClient
	Conf           *config.Config
	reportChan     chan ModuleReportInfo
	lastReportTime time.Time
}

// NewGM init new gm
func NewGM(conf *config.Config) (*GM, error) {
	var err error
	gdmToGmmChan := make(chan DoubleCheckInstanceInfo, 100)
	gmmToGqaChan := make(chan DoubleCheckInstanceInfo, 100)
	gqaToGcmChan := make(chan dbutil.DataBaseSwitch, 100)
	gm := &GM{
		Conf:           conf,
		reportChan:     make(chan ModuleReportInfo, 100),
		lastReportTime: time.Now(),
	}
	gm.gdm, err = NewGDM(conf, gdmToGmmChan, &HAReporter{
		gm:             gm,
		lastReportTime: time.Now(),
	})
	if err != nil {
		log.Logger.Errorf("gdm init failed. err:%s", err.Error())
		return nil, err
	}
	gm.gmm, err = NewGMM(gm.gdm, conf, gdmToGmmChan, gmmToGqaChan, &HAReporter{
		gm:             gm,
		lastReportTime: time.Now(),
	})
	if err != nil {
		log.Logger.Errorf("gmm init failed. err:%s", err.Error())
		return nil, err
	}
	gm.gqa, err = NewGQA(gm.gdm, conf, gmmToGqaChan, gqaToGcmChan, &HAReporter{
		gm:             gm,
		lastReportTime: time.Now(),
	})
	if err != nil {
		log.Logger.Errorf("gqa init failed. err:%s", err.Error())
		return nil, err
	}
	gm.gcm, err = NewGCM(conf, gqaToGcmChan, &HAReporter{
		gm:             gm,
		lastReportTime: time.Now(),
	})
	if err != nil {
		log.Logger.Errorf("gcm init failed. err:%s", err.Error())
		return nil, err
	}
	gm.HaDBClient, err = client.NewHaDBClient(&conf.DBConf.HADB, conf.GetCloudId())
	if err != nil {
		return nil, err
	}
	return gm, nil
}

// Run gm work main entry
func (gm *GM) Run() error {
	if err := gm.HaDBClient.RegisterDBHAInfo(util.LocalIp, gm.Conf.GMConf.ListenPort, "gm",
		gm.Conf.GMConf.City, gm.Conf.GMConf.Campus, ""); err != nil {
		return err
	}

	if err := gm.HaDBClient.RegisterDBHAInfo(util.LocalIp, gm.Conf.GMConf.ListenPort, constvar.GDM,
		gm.Conf.GMConf.City, gm.Conf.GMConf.Campus, ""); err != nil {
		log.Logger.Errorf("GM register gcm module failed,err:%s", err.Error())
		return err
	}

	go func() {
		gm.gdm.Run()
	}()

	if err := gm.HaDBClient.RegisterDBHAInfo(util.LocalIp, gm.Conf.GMConf.ListenPort, constvar.GMM,
		gm.Conf.GMConf.City, gm.Conf.GMConf.Campus, ""); err != nil {
		log.Logger.Errorf("GM register gcm module failed,err:%s", err.Error())
		return err
	}

	go func() {
		gm.gmm.Run()
	}()

	if err := gm.HaDBClient.RegisterDBHAInfo(util.LocalIp, gm.Conf.GMConf.ListenPort, constvar.GQA,
		gm.Conf.GMConf.City, gm.Conf.GMConf.Campus, ""); err != nil {
		log.Logger.Errorf("GM register gcm module failed,err:%s", err.Error())
		return err
	}

	go func() {
		gm.gqa.Run()
	}()

	if err := gm.HaDBClient.RegisterDBHAInfo(util.LocalIp, gm.Conf.GMConf.ListenPort, constvar.GCM,
		gm.Conf.GMConf.City, gm.Conf.GMConf.Campus, ""); err != nil {
		log.Logger.Errorf("GM register gcm module failed,err:%s", err.Error())
		return err
	}

	go func() {
		gm.gcm.Run()
	}()

	gm.TimerRun()
	return nil
}

// GetGDM return gdm object
func (gm *GM) GetGDM() *GDM {
	return gm.gdm
}

// GetGMM return gmm object
func (gm *GM) GetGMM() *GMM {
	return gm.gmm
}

// GetGQA return gqa object
func (gm *GM) GetGQA() *GQA {
	return gm.gqa
}

// GetGCM return gcm object
func (gm *GM) GetGCM() *GCM {
	return gm.gcm
}

// TimerRun gm report heartbeat
func (gm *GM) TimerRun() {
	for {
		select {
		case ins := <-gm.reportChan:
			gm.ProcessModuleReport(ins)
		case <-time.After(time.Duration(gm.Conf.GMConf.ReportInterval) * time.Second):
		}
		gm.CheckReportMyself()
	}
}

// ProcessModuleReport do module report
func (gm *GM) ProcessModuleReport(reportInfo ModuleReportInfo) {
	log.Logger.Infof("GM process module[%s] report", reportInfo.Module)
	gm.DoDBHAReport(reportInfo.Module)
}

// CheckReportMyself gm report itself heartbeat
func (gm *GM) CheckReportMyself() {
	now := time.Now()
	nextReport := gm.lastReportTime.Add(time.Duration(gm.Conf.GMConf.ReportInterval) * time.Second)
	if now.After(nextReport) {
		log.Logger.Debugf("GM report myself by check, lastReport:%s, now:%s, nextReport:%s",
			gm.lastReportTime.Format("2006-01-02 15:04:05"),
			now.Format("2006-01-02 15:04:05"),
			nextReport.Format("2006-01-02 15:04:05"))
		gm.lastReportTime = now
		gm.DoDBHAReport(constvar.GM)
	}
}

// DoDBHAReport do heartbeat report through api
func (gm *GM) DoDBHAReport(module string) {
	err := gm.HaDBClient.ReporterGMHeartbeat(module, gm.Conf.GMConf.ReportInterval)
	if err != nil {
		log.Logger.Errorf("report module[%s] heartbeat to dbha failed", module)
	} else {
		log.Logger.Infof("report module[%s] heartbeat to dbha ok", module)
	}
}

// GetDBDetect return instance detect info
func (dc *DoubleCheckInstanceInfo) GetDBDetect() *dbutil.DataBaseDetect {
	return &dc.db
}

// SetDBDetect set db detect info
func (dc *DoubleCheckInstanceInfo) SetDBDetect(detect dbutil.DataBaseDetect) {
	dc.db = detect
}

// DoReport gm do heartbeat report
func (reporter *HAReporter) DoReport(reportInfo ModuleReportInfo) {
	now := time.Now()
	nextReport := reporter.lastReportTime.Add(
		time.Duration(reporter.gm.Conf.GMConf.ReportInterval) * time.Second)
	if now.After(nextReport) {
		log.Logger.Debugf("report module[%s], lastReport:%s, now:%s, nextReport:%s",
			reportInfo.Module, reporter.lastReportTime.Format("2006-01-02 15:04:05"),
			now.Format("2006-01-02 15:04:05"), nextReport.Format("2006-01-02 15:04:05"))
		reporter.lastReportTime = now
		reporter.gm.DoDBHAReport(reportInfo.Module)
	}
}
