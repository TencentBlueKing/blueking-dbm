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
var passClient *client.PasswdClient
var (
	passwdCacheSize = 8000
	passwdCacheTime = 30 * time.Minute
)

func init() {
	passwdCache = NewLocked(passwdCacheSize)
}

func getPasswordClient(conf *config.Config) *client.PasswdClient {
	if passClient == nil {
		log.Logger.Infof("init password client for CloudID:%d, success.", conf.GetCloudId())
		passClient = client.NewPasswdClient(&conf.PasswdConf, conf.GetCloudId())
	}
	return passClient
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
func GetInstancePass(insArr []dbutil.DataBaseDetect, conf *config.Config) (int, error) {
	if len(insArr) == 0 {
		return 0, nil
	}
	pswdInsts, maxBatch := []client.PasswdInstance{}, 200
	clusterDuplicate := map[int]struct{}{}
	for _, ins := range insArr {
		if _, ok := clusterDuplicate[ins.GetClusterId()]; ok {
			continue
		}
		clusterDuplicate[ins.GetClusterId()] = struct{}{}

		if _, ok := passwdCache.Get(fmt.Sprintf("%d-%s", ins.GetClusterId(), constvar.ComponentRedis)); !ok {
			pswdInsts = append(pswdInsts, client.PasswdInstance{
				Ip:    strconv.Itoa(ins.GetClusterId()),
				Port:  0,
				Cloud: conf.GetCloudId(),
			})

			//Batch Get .
			if len(pswdInsts) >= maxBatch {
				batchGetPassword(pswdInsts, conf)
				pswdInsts = []client.PasswdInstance{}
			}
		}
	}
	//Get
	batchGetPassword(pswdInsts, conf)

	return 0, nil
}

// batchGetPassword batch get password and Set Password.
func batchGetPassword(pins []client.PasswdInstance, conf *config.Config) {
	if len(pins) == 0 {
		return
	}
	// need call password service api to fetch the password
	if newPasswds, err := getPasswordClient(conf).GetBatchPasswd(
		pins, GetRedisUserAndComponent(false), len(pins)*2+1); err != nil {
		log.Logger.Errorf("redis batch get password from remote failed:%s", err.Error())
	} else {
		for _, pwd := range newPasswds {
			pwByte, err := base64.StdEncoding.DecodeString(pwd.Passwd)
			if err != nil {
				log.Logger.Errorf("decode redis passwd failed clusterID:%s,dbType:%s:%+v", pwd.Ip, pwd.Component, pwd.Passwd)
				continue
			}
			exp := GetPassExpireTime()
			expireAfter := time.Now().Add(exp).Format("2006-01-02 15:04:05")
			log.Logger.Debugf("add_2_cache k:%s-%s, v:%s e:%s", pwd.Ip, pwd.Component, string(pwByte), expireAfter)
			passwdCache.Add(fmt.Sprintf("%s-%s", pwd.Ip, pwd.Component), string(pwByte), exp)
		}
	}
}

func getComponentName(dbType string) string {
	var component string
	if dbType == constvar.TwemproxyMetaType || dbType == constvar.PredixyMetaType {
		component = constvar.ComponentRedisProxy
	} else if dbType == constvar.RedisMetaType ||
		dbType == constvar.TendisplusMetaType || dbType == constvar.TendisSSDMetaType {
		component = constvar.ComponentRedis
	} else {
		component = constvar.ComponentRedisProxyAdmin
	}
	return component
}

func GetPassByClusterID(clusterID int, dbType string) string {
	instPswd, passComp := "t-v-t", getComponentName(dbType)
	if instPswd, ok := passwdCache.Get(fmt.Sprintf("%d-%s", clusterID, passComp)); ok {
		instPassword := instPswd.(string)
		if instPassword == "" {
			log.Logger.Warnf("cached password for clusterID:%d:%s, mayNULL,delete it.", clusterID, dbType)
			passwdCache.Remove(fmt.Sprintf("%d-%s", clusterID, passComp))
		}
		return instPassword
	}

	if passClient != nil {
		log.Logger.Infof("get no pass from cache, refetch CID:%d,dbType:%s", clusterID, dbType)
		if newPasswds, err := passClient.GetBatchPasswd([]client.PasswdInstance{
			{
				Ip:    strconv.Itoa(clusterID),
				Port:  0,
				Cloud: passClient.CloudId,
			},
		}, GetRedisUserAndComponent(false), 2); err == nil {
			for _, pw := range newPasswds {
				pwByte, pwErr := base64.StdEncoding.DecodeString(pw.Passwd)
				if pwErr != nil {
					log.Logger.Errorf("decode passwd[%s] failed by ClusterID:%d,dbType:%s", pw.Passwd, clusterID, dbType)
					continue
				}
				pwVal := string(pwByte)
				if passComp == pw.Component {
					instPswd = pwVal
				}
				exp := GetPassExpireTime()
				expireAfter := time.Now().Add(exp).Format("2006-01-02 15:04:05")
				log.Logger.Debugf("add_2_cache k:%s-%s, v:%s e:%s", pw.Ip, pw.Component, pwVal, expireAfter)
				passwdCache.Add(fmt.Sprintf("%s-%s", pw.Ip, pw.Component), pwVal, exp)
			}
			log.Logger.Debugf("get pass by remote ID:%d,type:%s,pass:%s,ddd:%s", clusterID, dbType, instPswd, passComp)
		}
	}
	return instPswd
}

// GetInstancePassByClusterId get password by cluster id
func GetInstancePassByClusterId(dbType string, clusterID int,
	conf *config.Config) (string, error) {
	var instPassword string
	if instPswd, ok := passwdCache.Get(fmt.Sprintf("%d-%s", clusterID, getComponentName(dbType))); ok {
		instPassword = instPswd.(string)
	} else {
		pins := []client.PasswdInstance{
			{
				Ip:    strconv.Itoa(clusterID),
				Port:  0,
				Cloud: conf.GetCloudId(),
			},
		}
		newPasswds, err := getPasswordClient(conf).GetBatchPasswd(pins, GetRedisUserAndComponent(false), 2)
		if err != nil {
			return "", err
		}

		for _, pw := range newPasswds {
			pwByte, pwErr := base64.StdEncoding.DecodeString(pw.Passwd)
			if pwErr != nil {
				log.Logger.Errorf("decode passwd[%s] failed", pw.Passwd)
				continue
			}

			pwVal := string(pwByte)
			if getComponentName(dbType) == pw.Component {
				instPassword = pwVal
			}
			passwdCache.Add(fmt.Sprintf("%d-%s", clusterID, getComponentName(dbType)), pwVal, GetPassExpireTime())
			log.Logger.Infof("reset password 2 cache ClusterID:%d-%s,DbType:%s", clusterID, getComponentName(dbType), dbType)
		}
	}
	return instPassword, nil
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
	newPasswds, err := getPasswordClient(conf).GetBatchPasswd(pins, uins, limit)
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

func GetPassExpireTime() time.Duration {
	n, _ := rand.Int(rand.Reader, big.NewInt(600))
	return passwdCacheTime + time.Duration(n.Int64())*time.Second
}
