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
	gqaCh chan DoubleCheckInstanceInfo, reporter *HAReporter) (*GMM, error) {
	var err error
	gmm := &GMM{
		GDMChan:  gdmCh,
		GQAChan:  gqaCh,
		gdm:      gdm,
		Conf:     conf,
		reporter: reporter,
	}
	gmm.HaDBClient, err = client.NewHaDBClient(&conf.DBConf.HADB, conf.GetCloudId())
	if err != nil {
		return nil, err
	}
	return gmm, nil
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
	checkStatus := instance.db.GetStatus()
	switch checkStatus {
	case constvar.SSHCheckSuccess:
		{ // machine level switch never satisfy this condition, agent only report ssh failed instance.
			ip, port := instance.db.GetAddress()
			// no switch in machine level switch
			gmm.HaDBClient.ReportHaLog(
				ip,
				port,
				"gmm",
				"db check failed. no need to switch in machine level",
			)
		}
	// AUTHCheckFailed also need double check and process base on the result of double check.
	case constvar.SSHCheckFailed, constvar.AUTHCheckFailed:
		{ // double check
			go func(doubleCheckInstance DoubleCheckInstanceInfo) {
				ip, port := doubleCheckInstance.db.GetAddress()
				err := doubleCheckInstance.db.Detection()
				switch doubleCheckInstance.db.GetStatus() {
				case constvar.DBCheckSuccess:
					gmm.HaDBClient.ReportHaLog(
						ip,
						port,
						"gmm",
						"double check success: db check success.",
					)
				case constvar.SSHCheckSuccess:
					{
						// no switch in machine level switch
						gmm.HaDBClient.ReportHaLog(
							ip,
							port,
							"gmm",
							fmt.Sprintf("double check success: db check failed, ssh check success. dbcheck err:%s", err),
						)
					}
				case constvar.SSHCheckFailed:
					{
						gmm.HaDBClient.ReportHaLog(
							ip,
							port,
							"gmm",
							fmt.Sprintf("double check failed: ssh check failed. sshcheck err:%s", err),
						)
						content := fmt.Sprintf("double check failed: ssh check failed. sshcheck err:%s", err)
						monitor.MonitorSendDetect(
							doubleCheckInstance.db, constvar.DBHAEventDoubleCheckSSH, content,
						)
						doubleCheckInstance.ResultInfo = content
						// reporter GQA
						doubleCheckInstance.ConfirmTime = time.Now()
						gmm.GQAChan <- doubleCheckInstance
						return
					}
				case constvar.AUTHCheckFailed:
					{
						log.Logger.Errorf("double check failed: ssh authenticate failed,err:%s", err)
						gmm.HaDBClient.ReportHaLog(
							ip,
							port,
							"gmm",
							fmt.Sprintf("double check failed: ssh authenticate failed, dbcheck err:%s", err),
						)
						content := fmt.Sprintf("double check failed: ssh authenticate failed. sshcheck err:%s", err)
						monitor.MonitorSendDetect(
							doubleCheckInstance.db, constvar.DBHAEventDoubleCheckAuth, content,
						)
					}
				default:
					log.Logger.Fatalf("unknown check status:%s", doubleCheckInstance.db.GetStatus())
				}
				gmm.gdm.InstanceSwitchDone(ip, port, string(doubleCheckInstance.db.GetType()))
			}(instance)
		}
	default:
		log.Logger.Errorf("unknown check status recevied: %s", checkStatus)
	}
}
