package exporter

import (
	"dbm-services/common/go-pubpkg/logger"
	reversemysqlapi "dbm-services/common/reverseapi/apis/mysql"
	reversemysqldef "dbm-services/common/reverseapi/define/mysql"
	"dbm-services/common/reverseapi/pkg/core"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"os"
)

type exporterConfig struct {
	Ip           string `json:"ip"`
	Port         int    `json:"port"`
	User         string `json:"user"`
	Password     string `json:"password"`
	MachineType  string `json:"machine_type"`
	InstanceRole string `json:"instance_role"`
}

func GenConfig(bkCloudId int64, nginxAddrs []string, ports ...int) error {
	apiCore, err := core.NewCoreWithAddr(bkCloudId, nginxAddrs, core.DefaultRetryOpts...)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	data, err := reversemysqlapi.ExporterConfig(apiCore, ports...)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	logger.Info("exporter config: %s", string(data))

	b, l, err := reversemysqlapi.ListInstanceInfo(apiCore)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	isSpiderMaster := false
	if l == "proxy" {
		var pis []reversemysqldef.ProxyInstanceInfo
		err = json.Unmarshal(b, &pis)
		if err != nil {
			logger.Error(err.Error())
			return err
		}

		isSpiderMaster = pis[0].MachineType == "spider" && pis[0].SpiderRole == "spider_master"
	}

	var exporterConfigs []exporterConfig
	err = json.Unmarshal(data, &exporterConfigs)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	for _, cfg := range exporterConfigs {
		err := genOne(&cfg)
		if err != nil {
			logger.Error(err.Error())
			return err
		}

		if isSpiderMaster {
			cfg.Port += 1000
			err = genOne(&cfg)
			if err != nil {
				logger.Error(err.Error())
				return err
			}
		}
	}

	return nil
}

func genOne(cfg *exporterConfig) error {
	if cfg.MachineType == "proxy" {
		return genOneProxy(cfg)
	} else {
		return genOneMySQL(cfg)
	}
}

func genOneProxy(cfg *exporterConfig) error {
	fp := fmt.Sprintf("/etc/exporter_%d.cnf", cfg.Port)
	f, err := os.OpenFile(fp, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0644)
	if err != nil {
		logger.Error(err.Error())
		return err
	}
	defer func() {
		_ = f.Close()
	}()

	content := fmt.Sprintf(
		`%s:%d,,,%s:%d,%s,%s`,
		cfg.Ip, cfg.Port,
		cfg.Ip, native.GetProxyAdminPort(cfg.Port),
		cfg.User, cfg.Password,
	)

	_, err = f.WriteString(content)
	if err != nil {
		logger.Error(err.Error())
		return err
	}
	return nil
}

func genOneMySQL(cfg *exporterConfig) error {
	fp := fmt.Sprintf("/etc/exporter_%d.cnf", cfg.Port)
	err := util.CreateExporterConf(fp, cfg.Ip, cfg.Port, cfg.User, cfg.Password, cfg.InstanceRole)
	if err != nil {
		logger.Error(err.Error())
		return err
	}
	return nil
}
