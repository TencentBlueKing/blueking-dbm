package gm

import (
	"fmt"
	"time"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/monitor"
)

// GMM work struct
type GMM struct {
	GDMChan    chan DoubleCheckInstanceInfo
	GQAChan    chan DoubleCheckInstanceInfo
	HaDBClient *client.HaDBClient
	gdm        *GDM
	Conf       *config.Config
	reporter   *HAReporter
}

// NewGMM new gmm obeject
func NewGMM(gdm *GDM, conf *config.Config, gdmCh,
	gqaCh chan DoubleCheckInstanceInfo, reporter *HAReporter) *GMM {
	return &GMM{
		GDMChan:    gdmCh,
		GQAChan:    gqaCh,
		gdm:        gdm,
		Conf:       conf,
		reporter:   reporter,
		HaDBClient: client.NewHaDBClient(&conf.DBConf.HADB, conf.GetCloudId()),
	}
}

// Run gmm main entry
func (gmm *GMM) Run() {
	for {
		select {
		case instance := <-gmm.GDMChan:
			gmm.Process(instance)
		case <-time.After(time.Duration(gmm.Conf.GMConf.ReportInterval) * time.Second):
		}
		gmm.reporter.DoReport(ModuleReportInfo{
			Module: constvar.GMM,
		})
	}
}

// PopInstance pop instance from gdm chan
func (gmm *GMM) PopInstance() DoubleCheckInstanceInfo {
	instance := <-gmm.GDMChan
	return instance
}

// PushInstance2Next push instance to gqa chan
func (gmm *GMM) PushInstance2Next(instance DoubleCheckInstanceInfo) {
	gmm.GQAChan <- instance
	return
}

// Process gmm process instance detect
func (gmm *GMM) Process(instance DoubleCheckInstanceInfo) {
	gmIP := gmm.Conf.GMConf.LocalIP
	checkStatus := instance.db.GetStatus()
	switch checkStatus {
	case constvar.SSHCheckSuccess:
		{ // machine level switch never satisfy this condition, agent only report ssh failed instance.
			ip, port := instance.db.GetAddress()
			// no switch in machine level switch
			gmm.HaDBClient.ReportHaLogRough(
				gmIP,
				instance.db.GetApp(),
				ip,
				port,
				"gmm",
				"db check failed. no need to switch in machine level",
			)
		}
	// SSHAuthFailed also need double-check and process base on the result of double check.
	case constvar.SSHCheckFailed, constvar.SSHAuthFailed, constvar.RedisAuthFailed:
		{ // double check
			go func(doubleCheckInstance DoubleCheckInstanceInfo) {
				ip, port := doubleCheckInstance.db.GetAddress()
				err := doubleCheckInstance.db.Detection()
				switch doubleCheckInstance.db.GetStatus() {
				case constvar.DBCheckSuccess:
					gmm.HaDBClient.ReportHaLogRough(
						gmIP,
						doubleCheckInstance.db.GetApp(),
						ip,
						port,
						"gmm",
						"double check success: db check ok.",
					)
				case constvar.SSHCheckSuccess:
					{
						// no switch in machine level switch
						gmm.HaDBClient.ReportHaLogRough(
							gmIP,
							doubleCheckInstance.db.GetApp(),
							ip,
							port,
							"gmm",
							fmt.Sprintf("double check success: db check failed, ssh check ok. dbcheck err:%s", err),
						)
					}
				case constvar.SSHCheckFailed, constvar.SSHAuthFailed:
					{
						content := fmt.Sprintf("double check failed: ssh check failed. sshcheck err:%s", err.Error())
						checkId, err := gmm.HaDBClient.ReportHaLog(
							gmIP,
							doubleCheckInstance.db.GetApp(),
							ip,
							port,
							"gmm",
							content,
						)
						if err != nil {
							log.Logger.Errorf(fmt.Sprintf("insert ha logs failed:%s", err.Error()))
							return
						}
						doubleCheckInstance.CheckID = checkId
						// ssh auth failed, report event also
						if doubleCheckInstance.db.GetStatus() == constvar.SSHAuthFailed {
							monitor.MonitorSendDetect(
								doubleCheckInstance.db, constvar.DBHAEventDoubleCheckSSH, content,
							)
						}
						monitor.MonitorSendDetect(
							doubleCheckInstance.db, constvar.DBHAEventDoubleCheckSSH, content,
						)
						doubleCheckInstance.ResultInfo = content
						// reporter GQA
						doubleCheckInstance.ConfirmTime = time.Now()
						gmm.GQAChan <- doubleCheckInstance
						return
					}
				case constvar.RedisAuthFailed:
					{
						content := fmt.Sprintf("database authenticate failed, err:%s", err.Error())
						log.Logger.Errorf(content)
						gmm.HaDBClient.ReportHaLogRough(
							gmIP,
							doubleCheckInstance.db.GetApp(),
							ip,
							port,
							"gmm",
							content,
						)
						monitor.MonitorSendDetect(
							doubleCheckInstance.db, constvar.DBHAEventDoubleCheckAuth, content,
						)
						log.Logger.Infof("database authenticate failed, skip switch")
					}
				default:
					log.Logger.Fatalf("unknown check status:%s", doubleCheckInstance.db.GetStatus())
				}
				gmm.gdm.InstanceSwitchDone(ip, port, string(doubleCheckInstance.db.GetDBType()))
			}(instance)
		}
	default:
		log.Logger.Errorf("unknown check status recevied: %s", checkStatus)
	}
}
