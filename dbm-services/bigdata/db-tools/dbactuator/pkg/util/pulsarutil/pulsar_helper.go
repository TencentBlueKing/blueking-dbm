package pulsarutil

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strconv"
	"strings"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"

	"gopkg.in/ini.v1"
)

// CheckBrokerConf TODO
func CheckBrokerConf(bkNum int) (err error) {
	// 获取broker.conf中的EnsembleSize、Qw、Qa
	brokerCfg, err := ini.Load(cst.DefaultPulsarBrokerConf)
	if err != nil {
		logger.Error("Failed to read config file %s, reason: %v", cst.DefaultPulsarBrokerConf, err)
		return err
	}
	ensembleSize := brokerCfg.Section("").Key("managedLedgerDefaultEnsembleSize").MustInt()
	writeQuorumSize := brokerCfg.Section("").Key("managedLedgerDefaultWriteQuorum").MustInt()
	ackQuorumSize := brokerCfg.Section("").Key("managedLedgerDefaultAckQuorum").MustInt()
	if bkNum >= ensembleSize && ensembleSize >= writeQuorumSize && writeQuorumSize >= ackQuorumSize {
		return nil
	} else {
		logger.Error("Bookie can be decommissioned only when Num(RemainBookie) >= EnsembleSize >= Qw >= Qa, "+
			"however, Num(RemainBookie)=%v, E=%v, Qw=%v, Qa=%v",
			bkNum, ensembleSize, writeQuorumSize, ackQuorumSize)
		return errors.New("num(RemainBookie) >= EnsembleSize >= Qw >= Qa is not satisfied")
	}
}

// GetAllTenant TODO
func GetAllTenant() ([]string, error) {
	// 获取所有租户名称
	extraCmd := fmt.Sprintf("%s/bin/pulsar-admin tenants list", cst.DefaultPulsarBrokerDir)
	logger.Info("获取所有租户, [%s]", extraCmd)
	tenantListStr, err := osutil.ExecShellCommand(false, extraCmd)
	if err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return nil, err
	}
	br := bufio.NewReader(strings.NewReader(tenantListStr))
	var tenantList []string
	for {
		line, _, err := br.ReadLine()
		if err != nil && len(line) == 0 {
			break
		}
		tenantList = append(tenantList, string(line))
	}
	return tenantList, nil
}

// GetAllNamespace TODO
func GetAllNamespace(tenant string) ([]string, error) {
	// 获取各个租户下的所有namespace
	extraCmd := fmt.Sprintf("%s/bin/pulsar-admin namespaces list %s", cst.DefaultPulsarBrokerDir, tenant)
	logger.Info("获取租户[%s]下的所有namespace, [%s]", tenant, extraCmd)
	namespaceListStr, err := osutil.ExecShellCommand(false, extraCmd)
	if err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return nil, err
	}
	br := bufio.NewReader(strings.NewReader(namespaceListStr))
	var namespaceList []string
	for {
		line, _, err := br.ReadLine()
		if err != nil && len(line) == 0 {
			break
		}
		namespaceList = append(namespaceList, string(line))
	}
	return namespaceList, nil
}

// CheckNamespaceEnsembleSize TODO
func CheckNamespaceEnsembleSize(bkNum int) (err error) {
	tenantsList, err := GetAllTenant()
	if err != nil {
		logger.Error("get all tenant error, %v", err)
		return err
	}
	for _, tenant := range tenantsList {
		namespaceList, err := GetAllNamespace(tenant)
		if err != nil {
			logger.Error("get all namespace failed, tenant=%s, error: %v", tenant, err)
			return err
		}
		for _, namespace := range namespaceList {
			extraCmd := fmt.Sprintf("%s/bin/pulsar-admin namespaces get-persistence %s",
				cst.DefaultPulsarBrokerDir, namespace)
			logger.Info("获取namespace[%s]持久化策略, [%s]", namespace, extraCmd)
			res, err := osutil.ExecShellCommand(false, extraCmd)
			if err != nil {
				logger.Error("[%s] execute failed, %v", err)
				return err
			}
			if res != "null\n" {
				persistence := make(map[string]interface{}, 0)
				if err := json.Unmarshal([]byte(res), &persistence); err == nil {
					ensembleSize := persistence["bookkeeperEnsemble"].(int)
					writeQuorumSize := persistence["bookkeeperWriteQuorum"].(int)
					ackQuorumSize := persistence["bookkeeperAckQuorum"].(int)
					if !(bkNum >= ensembleSize && ensembleSize >= writeQuorumSize && writeQuorumSize >= ackQuorumSize) {
						logger.Error("Bookie can be decommissioned only when Num(RemainBookie)>=EnsembleSize>="+
							"Qw>=Qa, however, Num(RemainBookie)=%v, E=%v, Qw=%v, Qa=%v",
							bkNum, ensembleSize, writeQuorumSize, ackQuorumSize)
						return errors.New("num(RemainBookie) > EnsembleSize >= Qw >= Qa is not satisfied")
					}
				} else {
					logger.Error("json unmarshal failed [%s], %v", res, err)
					return err
				}
			}
		}
	}
	return nil
}

// CheckUnderReplicated TODO
func CheckUnderReplicated() error {
	// 列出复制中的ledgers
	extraCmd := fmt.Sprintf("%s/bin/bookkeeper shell listunderreplicated | grep ListUnderReplicatedCommand",
		cst.DefaultPulsarBkDir)
	logger.Info("获取复制中的ledgers, [%s]", extraCmd)
	res, err := osutil.ExecShellCommand(false, extraCmd)
	if err != nil && len(res) > 0 {
		logger.Error("[%s] execute failed, %v", err)
		return err
	}
	if len(res) > 0 {
		logger.Error("under replicated: [%s]", res)
		return errors.New("bookie is under replicated")
	}
	return nil
}

// GetAllDataDir 获取所有/data*的路径
func GetAllDataDir() ([]string, error) {
	files, err := os.ReadDir("/")
	if err != nil {
		logger.Error("[%s] execute failed, %v", err)
		return nil, err
	}

	var dataDir []string
	for _, file := range files {
		if file.IsDir() && strings.HasPrefix(file.Name(), "data") {
			dataDir = append(dataDir, "/"+file.Name())
		}
	}
	return dataDir, nil
}

// CheckLedgerMetadata 检查ledger的metadata
func CheckLedgerMetadata(bookieNum int) (err error) {
	// 获取所有open状态ledger的元数据
	extraCmd := fmt.Sprintf("%s/bin/bookkeeper shell listledgers -m | grep \"ListLedgersCommand\" "+
		"| grep \"state=OPEN\" | cut -d \",\" -f 3,4,5", cst.DefaultPulsarBkDir)
	logger.Info("获取open状态的ledger, [%s]", extraCmd)
	ledgerMetadata, err := osutil.ExecShellCommand(false, extraCmd)
	if err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}
	br := bufio.NewReader(strings.NewReader(ledgerMetadata))

	for {
		line, _, err := br.ReadLine()
		if err != nil && len(line) == 0 {
			break
		}
		metadata := strings.Split(string(line), ",")
		ensembleStr := metadata[0]
		writeQuorumStr := metadata[1]
		ensembleSize, convErr := strconv.Atoi(strings.Split(ensembleStr, "=")[1])
		if convErr != nil {
			logger.Error("get ensemble size failed, str: %s, err: %v", ensembleStr, convErr)
			return convErr
		}
		writeQuorumSize, convErr := strconv.Atoi(strings.Split(writeQuorumStr, "=")[1])
		if convErr != nil {
			logger.Error("get write quorum size failed, str: %s, err: %v", writeQuorumStr, convErr)
			return convErr
		}
		if ensembleSize > bookieNum {
			logger.Error("ensembleSize(%d) can't be bigger than bookieNum(%d)", ensembleSize, bookieNum)
			return errors.New("ensembleSize > Num(bookie)")
		}
		if writeQuorumSize > bookieNum {
			logger.Error("writeQuorumSize(%d) can't be bigger than bookieNum(%d)", writeQuorumSize, bookieNum)
			return errors.New("writeQuorumSize > Num(bookie)")
		}
		if writeQuorumSize == 1 {
			logger.Error("some ledger's write quorum is 1, decommission may lead to data lost")
			return errors.New("writeQuorumSize = 1")
		}
	}
	return nil
}
