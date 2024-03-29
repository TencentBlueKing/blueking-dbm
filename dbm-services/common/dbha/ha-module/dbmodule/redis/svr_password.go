package redis

import (
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"math/big"
	"strconv"
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
	passwdCacheSize = 8000
	passwdCacheTime = 10 * time.Minute
)

func init() {
	passwdCache = NewLocked(passwdCacheSize)
}

// GetRedisMachinePasswd get redis machine password from remote dbconfig server
func GetRedisMachinePasswdDBConfig(
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
	passwdCache.Add(key, passwd, GetPassExpireTime())
	log.Logger.Debugf("RedisSSHPWD %s get passwd[%s] ok", key, passwd)
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
func GetInstancePassDBConfig(dbType types.DBType,
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
		passwdCache.Add(key, v, GetPassExpireTime())
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
func GetInstancePassByClusterDBConfig(dbType types.DBType,
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
		passwdCache.Add(key, passwdStr, GetPassExpireTime())
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

// RedisPasswd the redis password struct
type RedisPasswd struct {
	// redis password
	Redis string
	// proxy password
	Proxy string
	// proxy admin password
	ProxyAdmin string
}

// GetRedisUserAndComponent get redis user and component
func GetRedisUserAndComponent(isMachine bool) []client.PasswdUser {
	if isMachine {
		return []client.PasswdUser{
			client.PasswdUser{
				UserName:  constvar.UserMachineDefault,
				Component: constvar.ComponentRedis,
			},
		}
	} else {
		return []client.PasswdUser{
			{
				UserName:  constvar.UserRedisDefault,
				Component: constvar.ComponentRedis,
			},
			{
				UserName:  constvar.UserRedisDefault,
				Component: constvar.ComponentRedisProxy,
			},
		}
	}
}

// GetMachineInstance get machine instance array
func GetMachineInstance() []client.PasswdInstance {
	return []client.PasswdInstance{
		{
			Ip:    constvar.MachineInstanceDefault,
			Port:  0,
			Cloud: 0,
		},
	}
}

// GetInstancePass get redis instances cluster password by batch api
func GetInstancePass(insArr []dbutil.DataBaseDetect,
	conf *config.Config) (int, error) {
	cluster2Passwd := make(map[string]RedisPasswd)
	pins := make([]client.PasswdInstance, 0)
	uins := GetRedisUserAndComponent(false)
	limit := len(insArr)*2 + 1

	clusterExist := make(map[string]string)
	for _, ins := range insArr {
		key := fmt.Sprintf("%d-0", ins.GetClusterId())
		_, ok := clusterExist[key]
		if ok {
			continue
		}
		clusterExist[key] = ""
		passwdVal, ok := passwdCache.Get(key)
		if ok {
			passwdRedis := passwdVal.(RedisPasswd)
			cluster2Passwd[key] = passwdRedis
		} else {
			pins = append(pins, client.PasswdInstance{
				Ip:    strconv.Itoa(ins.GetClusterId()),
				Port:  0,
				Cloud: conf.GetCloudId(),
			})
		}
	}

	// need call password service api to fetch the password
	if len(pins) > 0 {
		c := client.NewPasswdClient(&conf.PasswdConf, conf.GetCloudId())
		newPasswds, err := c.GetBatchPasswd(pins, uins, limit)
		// if callback error, process continue, only print err info
		if err != nil || newPasswds == nil || len(newPasswds) == 0 {
			if err != nil {
				log.Logger.Errorf("GetInstancePassNew fetch remote err:%s",
					err.Error())
			} else {
				log.Logger.Errorf("GetInstancePassNew no passwd get,insNum:%d",
					len(insArr))
			}
		} else {
			// process each password
			for _, pw := range newPasswds {
				key := fmt.Sprintf("%s-0", pw.Ip)
				passwd, setCache := ProcessSinglePassword(key, pw, cluster2Passwd)
				if setCache {
					log.Logger.Debugf("passwd add cache, key:%s,passwd:%v", key, passwd)
					passwdCache.Add(key, passwd, GetPassExpireTime())
				}
			}
		}
	}

	// set password to detect instance
	succCount := 0
	for _, ins := range insArr {
		host, port := ins.GetAddress()
		key := fmt.Sprintf("%d-0", ins.GetClusterId())
		passwd, find := cluster2Passwd[key]
		if !find {
			log.Logger.Errorf("PassWDClusters ins[%s:%d] db[%s] not find cluster[%s] in passwds",
				host, port, ins.GetType(), ins.GetCluster())
		} else {
			err := SetPasswordToInstanceEx(ins.GetType(), passwd, ins)
			if err != nil {
				log.Logger.Errorf("PassWDClusters ins[%s:%d] db[%s] cluster[%s] set passwd[%v] fail",
					host, port, ins.GetType(), ins.GetCluster(), passwd)
			} else {
				succCount++
			}
		}
	}

	if succCount != len(insArr) {
		passErr := fmt.Errorf("PassWDClusters not all instance get passwd,succ:%d,all:%d",
			succCount, len(insArr))
		log.Logger.Errorf(passErr.Error())
		return succCount, passErr
	}

	log.Logger.Debugf("GetInstancePass succ:%d, input:%d",
		succCount, len(insArr))
	return succCount, nil
}

// ProcessSinglePassword pasre password and process
func ProcessSinglePassword(key string, pw client.PasswdItem,
	cluster2passwd map[string]RedisPasswd) (RedisPasswd, bool) {
	// password result struct
	var passwd RedisPasswd
	// flag control set cache or not
	setCache := false

	pwByte, pwErr := base64.StdEncoding.DecodeString(pw.Passwd)
	if pwErr != nil {
		log.Logger.Errorf("decode passwd[%s] failed", pw.Passwd)
		return passwd, setCache
	}

	pwVal := string(pwByte)
	tmp, find := cluster2passwd[key]
	if !find {
		if pw.Component == constvar.ComponentRedisProxy {
			cluster2passwd[key] = RedisPasswd{
				Proxy: pwVal,
			}
		} else if pw.Component == constvar.ComponentRedis {
			cluster2passwd[key] = RedisPasswd{
				Redis: pwVal,
			}
		} else {
			return passwd, setCache
		}
	} else {
		if pw.Component == constvar.ComponentRedisProxy {
			tmp.Proxy = pwVal
		} else if pw.Component == constvar.ComponentRedis {
			tmp.Redis = pwVal
		} else {
			return passwd, setCache
		}

		passwd = tmp
		cluster2passwd[key] = tmp
		if len(passwd.Redis) > 0 && len(passwd.Proxy) > 0 {
			setCache = true
		}
	}

	return passwd, setCache
}

// GetInstancePassByClusterId get password by cluster id
func GetInstancePassByClusterId(dbType string, clusterId int,
	conf *config.Config) (string, error) {
	var passwdCluster RedisPasswd
	key := fmt.Sprintf("%d-0", clusterId)
	passwdVal, ok := passwdCache.Get(key)
	if ok {
		passwdCluster = passwdVal.(RedisPasswd)
	} else {
		pins := []client.PasswdInstance{
			{
				Ip:    strconv.Itoa(clusterId),
				Port:  0,
				Cloud: conf.GetCloudId(),
			},
		}

		uins := GetRedisUserAndComponent(false)
		limit := 2
		c := client.NewPasswdClient(&conf.PasswdConf, conf.GetCloudId())
		newPasswds, err := c.GetBatchPasswd(pins, uins, limit)
		if err != nil {
			log.Logger.Errorf("GetBatchPasswd fetch remote err[%s]",
				err.Error())
			return "", err
		}

		if newPasswds == nil || len(newPasswds) == 0 {
			passErr := fmt.Errorf("call GetBatchPasswd return nil")
			log.Logger.Errorf(passErr.Error())
			return "", passErr
		}

		for _, pw := range newPasswds {
			pwByte, pwErr := base64.StdEncoding.DecodeString(pw.Passwd)
			if pwErr != nil {
				log.Logger.Errorf("decode passwd[%s] failed", pw.Passwd)
				continue
			}

			pwVal := string(pwByte)
			if pw.Component == constvar.ComponentRedisProxy {
				passwdCluster.Proxy = pwVal
			} else if pw.Component == constvar.ComponentRedis {
				passwdCluster.Redis = pwVal
			} else {
				continue
			}
		}

		// set password to cache
		if len(passwdCluster.Proxy) > 0 && len(passwdCluster.Redis) > 0 {
			passwdCache.Add(key, passwdCluster, GetPassExpireTime())
		}
	}

	if dbType == constvar.TwemproxyMetaType ||
		dbType == constvar.PredixyMetaType {
		return passwdCluster.Proxy, nil
	} else if dbType == constvar.RedisMetaType ||
		dbType == constvar.TendisplusMetaType ||
		dbType == constvar.TendisSSDMetaType {
		return passwdCluster.Redis, nil
	} else {
		typeErr := fmt.Errorf("GetInstancePassByClusterId dbtype[%s] not support",
			string(dbType))
		return "", typeErr
	}
}

// GetRedisMachinePasswd get redis machine password
func GetRedisMachinePasswd(
	conf *config.Config,
) string {
	format := "machine-%s"
	key := fmt.Sprintf(format, constvar.MachineInstanceDefault)

	// first read from cache
	cachePasswd, ok := passwdCache.Get(key)
	if ok {
		return cachePasswd.(string)
	}

	// request to password service
	uins := GetRedisUserAndComponent(true)
	pins := GetMachineInstance()
	limit := 1
	c := client.NewPasswdClient(&conf.PasswdConf, conf.GetCloudId())
	newPasswds, err := c.GetBatchPasswd(pins, uins, limit)
	if err != nil {
		log.Logger.Errorf("RedisSSHPWD fetch remote err[%s],return conf,pass:%s",
			err.Error(), conf.SSH.Pass)
		return conf.SSH.Pass
	}

	var passwd string
	if newPasswds == nil || len(newPasswds) == 0 {
		return conf.SSH.Pass
	}

	// parse password
	for _, pw := range newPasswds {
		pwByte, pwErr := base64.StdEncoding.DecodeString(pw.Passwd)
		if pwErr != nil {
			log.Logger.Errorf("decode passwd[%s] failed", pw.Passwd)
			continue
		}

		passwd = string(pwByte)
		break
	}

	// set password to cache
	passwdCache.Add(key, passwd, GetPassExpireTime())
	return passwd
}

// SetPasswordToInstanceEx set password to redis detection instance
func SetPasswordToInstanceEx(dbType types.DBType,
	passwd RedisPasswd, ins dbutil.DataBaseDetect) error {
	if dbType == constvar.RedisMetaType ||
		dbType == constvar.TendisSSDMetaType {
		cacheP, isCache := ins.(*RedisDetectInstance)
		if isCache {
			cacheP.Pass = passwd.Redis
		} else {
			passErr := fmt.Errorf("the type[%s] of instance transfer type failed", dbType)
			return passErr
		}
	} else if dbType == constvar.TwemproxyMetaType {
		twemP, isTwem := ins.(*TwemproxyDetectInstance)
		if isTwem {
			twemP.Pass = passwd.Proxy
		} else {
			passErr := fmt.Errorf("the type[%s] of instance transfer type failed", dbType)
			return passErr
		}
	} else if dbType == constvar.PredixyMetaType {
		predixyP, isPredixy := ins.(*PredixyDetectInstance)
		if isPredixy {
			predixyP.Pass = passwd.Proxy
		} else {
			passErr := fmt.Errorf("the type[%s] of instance transfer type failed", dbType)
			return passErr
		}
	} else if dbType == constvar.TendisplusMetaType {
		tendisP, isTendis := ins.(*TendisplusDetectInstance)
		if isTendis {
			tendisP.Pass = passwd.Redis
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

func GetPassExpireTime() time.Duration {
	n, _ := rand.Int(rand.Reader, big.NewInt(600))
	return passwdCacheTime + time.Duration(n.Int64())*time.Second
}
