package redis

import (
	"fmt"
	"time"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/types"
)

var passwdCache Cache
var (
	passwdCacheSize = 3000
	passwdCacheTime = 10 * time.Minute
)

func init() {
	passwdCache = NewLocked(passwdCacheSize)
}

// GetRedisMachinePasswd get redis machine password from remote dbconfig server
func GetRedisMachinePasswd(
	app string, conf *config.Config,
) string {
	format := "%s-%s-%s-%s-%s-%s-%s"
	key := fmt.Sprintf(format, app, constvar.ConfOSFile, constvar.ConfOSType,
		"", constvar.ConfOSApp, app, constvar.ConfCommon)

	cachePasswd, ok := passwdCache.Get(key)
	if ok {
		log.Logger.Debugf("RedisSSHPWD get cache ok, key:%s,passwd:%s",
			key, cachePasswd)
		return cachePasswd.(string)
	}

	passwdMap, err := GetMachinePasswordRemote(app, constvar.ConfOSFile,
		constvar.ConfOSType, "", constvar.ConfOSApp, app,
		constvar.ConfCommon, conf.NameServices.RemoteConf, conf.GetCloudId())
	if err != nil {
		log.Logger.Errorf("RedisSSHPWD fetch remote err[%s],return conf,pass:%s",
			err.Error(), conf.SSH.Pass)
		return conf.SSH.Pass
	}

	passwdVal, ok := passwdMap[constvar.ConfUserPasswd]
	if !ok {
		log.Logger.Errorf("RedisSSHPWD not find [%s] in map[%v]",
			constvar.ConfUserPasswd, passwdMap)
		return conf.SSH.Pass
	}

	passwd := passwdVal.(string)
	passwdCache.Add(key, passwd, passwdCacheTime)
	log.Logger.Debugf("RedisSSHPWD %s get passwd[%s] ok", key, passwd)
	return passwd
}

// GetMysqlMachinePasswd get mysql machine password from remote dbconfig server
func GetMysqlMachinePasswd(
	conf *config.Config,
) string {
	format := "%s-%s-%s-%s-%s-%s-%s"
	key := fmt.Sprintf(format, "0", constvar.ConfMysqlFile, constvar.ConfMysqlType,
		constvar.ConfMysqlName, constvar.ConfOSPlat, "0", constvar.ConfMysqlNamespace)

	cachePasswd, ok := passwdCache.Get(key)
	if ok {
		log.Logger.Debugf("MysqlSSHPWD get cache ok, key:%s,passwd:%s",
			key, cachePasswd)
		return cachePasswd.(string)
	}

	passwdMap, err := GetMachinePasswordRemote("0", constvar.ConfMysqlFile,
		constvar.ConfMysqlType, constvar.ConfMysqlName, constvar.ConfOSPlat,
		"0", constvar.ConfMysqlNamespace, conf.NameServices.RemoteConf, conf.GetCloudId())
	if err != nil {
		log.Logger.Errorf("MysqlSSHPWD fetch remote err[%s],return conf,pass:%s",
			err.Error(), conf.SSH.Pass)
		return conf.SSH.Pass
	}

	passwdVal, ok := passwdMap["os_mysql_pwd"]
	if !ok {
		log.Logger.Errorf("MysqlSSHPWD not find [%s] in map[%v]",
			constvar.ConfUserPasswd, passwdMap)
		return conf.SSH.Pass
	}

	passwd := passwdVal.(string)
	passwdCache.Add(key, passwd, passwdCacheTime)
	log.Logger.Debugf("MysqlSSHPWD %s get passwd[%s] ok", key, passwd)
	return passwd
}

// GetMachinePasswordRemote get machine password from remote dbconfig server
func GetMachinePasswordRemote(app string, confFile string, confType string,
	confName string, levelName string, levelValue string, namespace string,
	remoteconf config.APIConfig, cloudId int) (map[string]interface{}, error) {
	remoteConfigClient := client.NewRemoteConfigClient(&remoteconf, cloudId)

	configData, err := remoteConfigClient.GetConfigItem(
		app, confFile, confType, confName,
		levelName, levelValue, namespace,
	)
	if err != nil {
		log.Logger.Errorf("SSHPWD call failed,err:%s", err.Error())
		return make(map[string]interface{}), err
	}

	if configData == nil || len(configData) == 0 {
		passErr := fmt.Errorf("SSHPWD no config data")
		return make(map[string]interface{}), passErr
	}

	content, cok := configData[0]["content"]
	if !cok {
		passErr := fmt.Errorf("SSHPWD content not exist")
		log.Logger.Errorf(passErr.Error())
		return make(map[string]interface{}), passErr
	}

	passwdMap, pok := content.(map[string]interface{})
	if !pok {
		passErr := fmt.Errorf("SSHPWD transfer type failed")
		log.Logger.Errorf(passErr.Error())
		return make(map[string]interface{}), passErr
	}

	return passwdMap, nil
}

// GetInstancePass get redis instances cluster password by batch api
func GetInstancePass(dbType types.DBType,
	insArr []dbutil.DataBaseDetect, conf *config.Config) (int, error) {
	if dbType == constvar.DetectTenDBHA || dbType == constvar.DetectTenDBCluster {
		return 0, nil
	}

	cType, cFile, cName, lName, namespace, err := GetConfigParamByDbType(dbType)
	if err != nil {
		passErr := fmt.Errorf("PassWDClusters get passwd by dbtype[%s] failed", dbType)
		log.Logger.Errorf(passErr.Error())
		return 0, passErr
	}

	clusterPasswd := make(map[string]string)
	clusters := make([]string, 0)
	clusterExist := make(map[string]string)
	for _, ins := range insArr {
		_, ok := clusterExist[ins.GetCluster()]
		if ok {
			continue
		}
		clusterExist[ins.GetCluster()] = ""

		key := fmt.Sprintf("%s-%s-%s-%s-%s-%s",
			cFile, cType, cName, lName, namespace, ins.GetCluster())
		passwdVal, ok := passwdCache.Get(key)
		if ok {
			passwdStr := passwdVal.(string)
			clusterPasswd[ins.GetCluster()] = passwdStr
		} else {
			clusters = append(clusters, ins.GetCluster())
		}
	}
	log.Logger.Debugf("PassWDClusters cachePasswd:%v,NeedQuery:%v",
		clusterPasswd, clusters)

	remoteConfigClient := client.NewRemoteConfigClient(&conf.NameServices.RemoteConf, conf.GetCloudId())

	NewPasswds := QueryPasswords(remoteConfigClient, cFile,
		cType, cName, lName, clusters, namespace)
	for k, v := range NewPasswds {
		clusterPasswd[k] = v
		key := fmt.Sprintf("%s-%s-%s-%s-%s-%s",
			cFile, cType, cName, lName, namespace, k)
		passwdCache.Add(key, v, passwdCacheTime)
	}

	succCount := 0
	for _, ins := range insArr {
		host, port := ins.GetAddress()
		passwd, find := clusterPasswd[ins.GetCluster()]
		if !find {
			log.Logger.Errorf("PassWDClusters ins[%s:%d] db[%s] not find cluster[%s] in passwds",
				host, port, dbType, ins.GetCluster())
		} else {
			err := SetPasswordToInstance(dbType, passwd, ins)
			if err != nil {
				log.Logger.Errorf("PassWDClusters ins[%s:%d] db[%s] cluster[%s] set passwd[%s] fail",
					host, port, dbType, ins.GetCluster(), passwd)
			} else {
				succCount++
			}
		}
	}

	if succCount != len(insArr) {
		passErr := fmt.Errorf("PassWDClusters not all instance get passwd,dbtype:%s,succ:%d,all:%d",
			dbType, succCount, len(insArr))
		log.Logger.Errorf(passErr.Error())
		return succCount, passErr
	}
	return succCount, nil
}

// GetInstancePassByCluster get single redis cluster password
func GetInstancePassByCluster(dbType types.DBType,
	cluster string, conf *config.Config) (string, error) {
	if dbType == constvar.DetectTenDBHA || dbType == constvar.DetectTenDBCluster {
		return "", nil
	}

	cType, cFile, cName, lName, namespace, err := GetConfigParamByDbType(dbType)
	if err != nil {
		passErr := fmt.Errorf("PassWDCluster get passwd by dbtype[%s] failed", dbType)
		log.Logger.Errorf(passErr.Error())
		return "", passErr
	}

	key := fmt.Sprintf("%s-%s-%s-%s-%s-%s",
		cFile, cType, cName, lName, namespace, cluster)
	cachePasswd, ok := passwdCache.Get(key)
	if ok {
		return cachePasswd.(string), nil
	}

	remoteConfigClient := client.NewRemoteConfigClient(&conf.NameServices.RemoteConf, conf.GetCloudId())
	clusterPasswds := QueryPasswords(remoteConfigClient, cFile,
		cType, cName, lName, []string{cluster}, namespace)

	passwdStr, ok := clusterPasswds[cluster]
	if ok {
		passwdCache.Add(key, passwdStr, passwdCacheTime)
		return passwdStr, nil
	} else {
		passErr := fmt.Errorf("PassWDCluster key[%s] unfind passwd", key)
		log.Logger.Errorf(passErr.Error())
		return "", passErr
	}
}

// QueryPasswords the batch api of query password by input parameters
func QueryPasswords(remoteConfigClient *client.RemoteConfigClient, cFile string,
	cType string, cName string, lName string,
	clusters []string, namespace string) map[string]string {
	clusterPasswd := make(map[string]string)
	configData, err := remoteConfigClient.BatchGetConfigItem(
		cFile, cType, cName,
		lName, clusters, namespace,
	)
	if err != nil {
		log.Logger.Errorf(err.Error())
		return clusterPasswd
	}
	content, cok := configData["content"]
	if !cok {
		passErr := fmt.Errorf("PassWDQuery content not exist")
		log.Logger.Errorf(passErr.Error())
		return clusterPasswd
	}

	passwdMap, pok := content.(map[string]interface{})
	if !pok {
		passErr := fmt.Errorf("PassWDQuery transfer type failed")
		log.Logger.Errorf(passErr.Error())
		return clusterPasswd
	}

	for _, c := range clusters {
		passwdInfo, find := passwdMap[c]
		if !find {
			log.Logger.Errorf("PassWDQuery can not find passwd for cluster[%s]", c)
			continue
		}

		cname2passwd, ok := passwdInfo.(map[string]interface{})
		if !ok {
			log.Logger.Errorf("PassWDQuery [%v] trans to map[string]interface{} failed",
				passwdInfo)
			continue
		}

		passwd, ok := cname2passwd[cName]
		if !ok {
			log.Logger.Errorf("PassWDQuery not find [%s] in cname2passwd[%v]",
				cName, cname2passwd)
			continue
		}
		clusterPasswd[c] = passwd.(string)
	}
	return clusterPasswd
}

// SetPasswordToInstance set password to redis detection instance
func SetPasswordToInstance(dbType types.DBType,
	passwd string, ins dbutil.DataBaseDetect) error {
	if dbType == constvar.RedisMetaType {
		cacheP, isCache := ins.(*RedisDetectInstance)
		if isCache {
			cacheP.Pass = passwd
		} else {
			passErr := fmt.Errorf("the type[%s] of instance transfer type failed", dbType)
			return passErr
		}
	} else if dbType == constvar.TwemproxyMetaType {
		twemP, isTwem := ins.(*TwemproxyDetectInstance)
		if isTwem {
			twemP.Pass = passwd
		} else {
			passErr := fmt.Errorf("the type[%s] of instance transfer type failed", dbType)
			return passErr
		}
	} else if dbType == constvar.PredixyMetaType {
		predixyP, isPredixy := ins.(*PredixyDetectInstance)
		if isPredixy {
			predixyP.Pass = passwd
		} else {
			passErr := fmt.Errorf("the type[%s] of instance transfer type failed", dbType)
			return passErr
		}
	} else if dbType == constvar.TendisplusMetaType {
		tendisP, isTendis := ins.(*TendisplusDetectInstance)
		if isTendis {
			tendisP.Pass = passwd
		} else {
			passErr := fmt.Errorf("the type[%s] of instance transfer type failed", dbType)
			return passErr
		}
	} else {
		passwdErr := fmt.Errorf("the type[%s] of instance is invalid",
			dbType)
		return passwdErr
	}
	return nil
}

// GetConfigParamByDbType the return value:
//
//	conf_type conf_file conf_name conf_name level_name namespace
func GetConfigParamByDbType(dbType types.DBType,
) (string, string, string, string, string, error) {
	if dbType == constvar.RedisMetaType {
		clusterMeta := constvar.RedisCluster
		return "proxyconf", "Twemproxy-latest", "redis_password", "cluster", clusterMeta, nil
	} else if dbType == constvar.TwemproxyMetaType {
		clusterMeta := constvar.RedisCluster
		return "proxyconf", "Twemproxy-latest", "password", "cluster", clusterMeta, nil
	} else if dbType == constvar.PredixyMetaType {
		clusterMeta := constvar.TendisplusCluster
		return "proxyconf", "Predixy-latest", "password", "cluster", clusterMeta, nil
	} else if dbType == constvar.TendisplusMetaType {
		clusterMeta := constvar.TendisplusCluster
		return "proxyconf", "Predixy-latest", "redis_password", "cluster", clusterMeta, nil
	} else {
		return "", "", "", "", "", nil
	}
}
