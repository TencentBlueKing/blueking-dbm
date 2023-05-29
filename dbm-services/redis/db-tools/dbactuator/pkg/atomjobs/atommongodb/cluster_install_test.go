package atommongodb

import (
	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomsys"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"fmt"
	"net"
	"path"
	"strings"
	"testing"
	"time"
)

// TestShard1 安装shard1测试
func TestShard1(t *testing.T) {
	// 设置环境变量
	err := consts.SetMongoDataDir("")
	if err != nil {
		fmt.Println(fmt.Sprintf("Shard1 install SetMongoData fail, error:%s", err))
		t.Errorf("Shard1 install SetMongoData fail, error:%s", err)
		return
	}
	err = consts.SetMongoBackupDir("")
	if err != nil {
		fmt.Println(fmt.Sprintf("Shard1 install SetMongoBackup fail, error:%s", err))
		t.Errorf("Shard1 install SetMongoBackup fail, error:%s", err)
		return
	}

	err = consts.SetProcessUser("")
	if err != nil {
		fmt.Println(fmt.Sprintf("Shard1 install SetProcessUser fail, error:%s", err))
		t.Errorf("Shard1 install SetProcessUser fail, error:%s", err)
		return
	}
	err = consts.SetProcessUserGroup("")
	if err != nil {
		fmt.Println(fmt.Sprintf("Shard1 install SetProcessUserGroup fail, error:%s", err))
		t.Errorf("Shard1 install SetProcessUserGroup fail, error:%s", err)
		return
	}

	// 初始化节点
	osSysInitParam := "{\n\"user\":\"mysql\",\n\"password\":\"Qwe123d\"\n}"
	osSysInit := &atomsys.OsMongoInit{}
	osSysInitRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: osSysInitParam,
	}
	osSysInitRuntime.SetLogger()
	if err := osSysInit.Init(osSysInitRuntime); err != nil {
		fmt.Println(fmt.Sprintf("shard1 replicate install osSysInit init fail, error:%s", err))
		t.Errorf("shard1 replicate install osSysInit init fail, error:%s", err)
		return
	}
	if err := osSysInit.Run(); err != nil {
		fmt.Println(fmt.Sprintf("shard1 replicate install osSysInit run fail, error:%s", err))
		t.Errorf("shard1 replicate install osSysInit run fail, error:%s", err)
		return
	}

	// 获取本机IP地址
	var ip string
	addrs, _ := net.InterfaceAddrs()
	for _, addr := range addrs {
		if !strings.Contains(addr.String(), "127.0.0.1") {
			ip = strings.Split(addr.String(), "/")[0]
			break
		}
	}

	// node1
	node1 := "{\n  \"mediapkg\":{\n    \"pkg\":\"mongodb-linux-x86_64-3.4.20.tar.gz\",\n    \"pkg_md5\":\"e68d998d75df81b219e99795dec43ffb\"\n  },\n  \"ip\":\"{{ip}}\",\n  \"port\":27001,\n  \"dbVersion\":\"3.4.20\",\n  \"instanceType\":\"mongod\",\n  \"app\":\"test\",\n  \"areaId\":\"test1\",\n  \"setId\":\"s1\",\n  \"auth\": true,\n  \"clusterRole\":\"shardsvr\",\n  \"dbConfig\":{\n    \"slowOpThresholdMs\":200,\n    \"cacheSizeGB\":1,\n    \"oplogSizeMB\":500,\n    \"destination\":\"file\"\n  }\n}"
	node1 = strings.Replace(node1, "{{ip}}", ip, -1)

	// node2
	node2 := "{\n  \"mediapkg\":{\n    \"pkg\":\"mongodb-linux-x86_64-3.4.20.tar.gz\",\n    \"pkg_md5\":\"e68d998d75df81b219e99795dec43ffb\"\n  },\n  \"ip\":\"{{ip}}\",\n  \"port\":27002,\n  \"dbVersion\":\"3.4.20\",\n  \"instanceType\":\"mongod\",\n  \"app\":\"test\",\n  \"areaId\":\"test1\",\n  \"setId\":\"s1\",\n  \"auth\": true,\n  \"clusterRole\":\"shardsvr\",\n  \"dbConfig\":{\n    \"slowOpThresholdMs\":200,\n    \"cacheSizeGB\":1,\n    \"oplogSizeMB\":500,\n    \"destination\":\"file\"\n  }\n}"
	node2 = strings.Replace(node2, "{{ip}}", ip, -1)

	// node3
	node3 := "{\n  \"mediapkg\":{\n    \"pkg\":\"mongodb-linux-x86_64-3.4.20.tar.gz\",\n    \"pkg_md5\":\"e68d998d75df81b219e99795dec43ffb\"\n  },\n  \"ip\":\"{{ip}}\",\n  \"port\":27003,\n  \"dbVersion\":\"3.4.20\",\n  \"instanceType\":\"mongod\",\n  \"app\":\"test\",\n  \"areaId\":\"test1\",\n  \"setId\":\"s1\",\n  \"auth\": true,\n  \"clusterRole\":\"shardsvr\",\n  \"dbConfig\":{\n    \"slowOpThresholdMs\":200,\n    \"cacheSizeGB\":1,\n    \"oplogSizeMB\":500,\n    \"destination\":\"file\"\n  }\n}"
	node3 = strings.Replace(node3, "{{ip}}", ip, -1)

	node1MongodInstall := NewMongoDBInstall()
	node2MongodInstall := NewMongoDBInstall()
	node3MongodInstall := NewMongoDBInstall()

	node1Runtime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: node1,
	}
	node1Runtime.SetLogger()
	node2Runtime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: node2,
	}
	node2Runtime.SetLogger()
	node3Runtime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: node3,
	}
	node3Runtime.SetLogger()

	// 安装节点
	if err := node1MongodInstall.Init(node1Runtime); err != nil {
		fmt.Println(fmt.Sprintf("shard1 replicate install node1 init fail, error:%s", err))
		t.Errorf("shard1 replicate install node1 init fail, error:%s", err)
		return
	}
	if err := node1MongodInstall.Run(); err != nil {
		fmt.Println(fmt.Sprintf("shard1 replicate install node1 run fail, error:%s", err))
		t.Errorf("shard1 replicate install node1 run fail, error:%s", err)
		return
	}
	if err := node2MongodInstall.Init(node2Runtime); err != nil {
		fmt.Println(fmt.Sprintf("shard1 replicate install node2 init fail, error:%s", err))
		t.Errorf("shard1 replicate install node2 init fail, error:%s", err)
		return
	}
	if err := node2MongodInstall.Run(); err != nil {
		fmt.Println(fmt.Sprintf("shard1 replicate install node2 run fail, error:%s", err))
		t.Errorf("shard1 replicate install node2 run fail, error:%s", err)
		return
	}
	if err := node3MongodInstall.Init(node3Runtime); err != nil {
		fmt.Println(fmt.Sprintf("shard1 replicate install node3 init fail, error:%s", err))
		t.Errorf("shard1 replicate install node3 init fail, error:%s", err)
		return
	}
	if err := node3MongodInstall.Run(); err != nil {
		fmt.Println(fmt.Sprintf("shard1 replicate install node3 run fail, error:%s", err))
		t.Errorf("shard1 replicate install node3 run fail, error:%s", err)
		return
	}

	// 复制集初始化
	initReplicasetParam := "{\n  \"ip\":\"{{ip}}\",\n  \"port\":27001,\n  \"app\":\"test\",\n  \"areaId\":\"test1\",\n  \"setId\":\"s1\",\n  \"configSvr\":false,\n  \"ips\":[\n    \"{{ip}}:27001\",\n    \"{{ip}}:27002\",\n    \"{{ip}}:27003\"\n  ],\n  \"priority\":{\n    \"{{ip}}:27001\":1,\n    \"{{ip}}:27002\":1,\n    \"{{ip}}:27003\":0\n  },\n  \"hidden\":{\n    \"{{ip}}:27001\":false,\n    \"{{ip}}:27002\":false,\n    \"{{ip}}:27003\":true\n  }\n}"
	initReplicasetParam = strings.Replace(initReplicasetParam, "{{ip}}", ip, -1)
	initReplicasetRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: initReplicasetParam,
	}
	initReplicasetRuntime.SetLogger()
	initReplicaset := NewInitiateReplicaset()
	if err := initReplicaset.Init(initReplicasetRuntime); err != nil {
		fmt.Println(fmt.Sprintf("shard1 replicate install initReplicaset init fail, error:%s", err))
		t.Errorf("shard1 replicate install initReplicaset init fail, error:%s", err)
		return
	}
	if err := initReplicaset.Run(); err != nil {
		fmt.Println(fmt.Sprintf("shard1 replicate install initReplicaset run fail, error:%s", err))
		t.Errorf("shard1 replicate install initReplicaset run fail, error:%s", err)
		return
	}
	time.Sleep(time.Second * 3)
	// 创建管理员用户
	addAdminUserParam := "{\n  \"ip\":\"{{ip}}\",\n  \"port\":27001,\n  \"instanceType\":\"mongod\",\n  \"username\":\"dba\",\n  \"password\":\"dba\",\n  \"adminUsername\":\"\",\n  \"adminPassword\":\"\",\n  \"authDb\":\"admin\",\n  \"dbs\":[\n\n  ],\n  \"privileges\":[\n    \"root\"\n  ]\n}"
	addAdminUserParam = strings.Replace(addAdminUserParam, "{{ip}}", ip, -1)
	addAdminUserRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: addAdminUserParam,
	}
	addAdminUserRuntime.SetLogger()
	addAdminUser := NewAddUser()
	if err := addAdminUser.Init(addAdminUserRuntime); err != nil {
		fmt.Println(fmt.Sprintf("shard1 replicate install addAdminUser init fail, error:%s", err))
		t.Errorf("shard1 replicate install addAdminUser init fail, error:%s", err)
		return
	}
	if err := addAdminUser.Run(); err != nil {
		fmt.Println(fmt.Sprintf("shard1 replicate install addAdminUser run fail, error:%s", err))
		t.Errorf("shard1 replicate install addAdminUser run fail, error:%s", err)
		return
	}
}

// TestShard2 安装shard2测试
func TestShard2(t *testing.T) {
	// 设置环境变量
	err := consts.SetMongoDataDir("")
	if err != nil {
		fmt.Println(fmt.Sprintf("Shard2 install SetMongoData fail, error:%s", err))
		t.Errorf("Shard2 install SetMongoData fail, error:%s", err)
		return
	}
	err = consts.SetMongoBackupDir("")
	if err != nil {
		fmt.Println(fmt.Sprintf("Shard2 install SetMongoBackup fail, error:%s", err))
		t.Errorf("Shard2 install SetMongoBackup fail, error:%s", err)
		return
	}

	err = consts.SetProcessUser("")
	if err != nil {
		fmt.Println(fmt.Sprintf("Shard2 install SetProcessUser fail, error:%s", err))
		t.Errorf("Shard2 install SetProcessUser fail, error:%s", err)
		return
	}
	err = consts.SetProcessUserGroup("")
	if err != nil {
		fmt.Println(fmt.Sprintf("Shard2 install SetProcessUserGroup fail, error:%s", err))
		t.Errorf("Shard2 install SetProcessUserGroup fail, error:%s", err)
		return
	}

	// 初始化节点
	osSysInitParam := "{\n\"user\":\"mysql\",\n\"password\":\"Qwe123d\"\n}"
	osSysInit := &atomsys.OsMongoInit{}
	osSysInitRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: osSysInitParam,
	}
	osSysInitRuntime.SetLogger()
	if err := osSysInit.Init(osSysInitRuntime); err != nil {
		fmt.Println(fmt.Sprintf("shard2 replicate install osSysInit init fail, error:%s", err))
		t.Errorf("shard2 replicate install osSysInit init fail, error:%s", err)
		return
	}
	if err := osSysInit.Run(); err != nil {
		fmt.Println(fmt.Sprintf("shard2 replicate install osSysInit run fail, error:%s", err))
		t.Errorf("shard2 replicate install osSysInit run fail, error:%s", err)
		return
	}

	// 获取本机IP地址
	var ip string
	addrs, _ := net.InterfaceAddrs()
	for _, addr := range addrs {
		if !strings.Contains(addr.String(), "127.0.0.1") {
			ip = strings.Split(addr.String(), "/")[0]
			break
		}
	}

	// node1
	node1 := "{\n  \"mediapkg\":{\n    \"pkg\":\"mongodb-linux-x86_64-3.4.20.tar.gz\",\n    \"pkg_md5\":\"e68d998d75df81b219e99795dec43ffb\"\n  },\n  \"ip\":\"{{ip}}\",\n  \"port\":27005,\n  \"dbVersion\":\"3.4.20\",\n  \"instanceType\":\"mongod\",\n  \"app\":\"test\",\n  \"areaId\":\"test1\",\n  \"setId\":\"s2\",\n  \"auth\": true,\n  \"clusterRole\":\"shardsvr\",\n  \"dbConfig\":{\n    \"slowOpThresholdMs\":200,\n    \"cacheSizeGB\":1,\n    \"oplogSizeMB\":500,\n    \"destination\":\"file\"\n  }\n}"
	node1 = strings.Replace(node1, "{{ip}}", ip, -1)

	// node2
	node2 := "{\n  \"mediapkg\":{\n    \"pkg\":\"mongodb-linux-x86_64-3.4.20.tar.gz\",\n    \"pkg_md5\":\"e68d998d75df81b219e99795dec43ffb\"\n  },\n  \"ip\":\"{{ip}}\",\n  \"port\":27006,\n  \"dbVersion\":\"3.4.20\",\n  \"instanceType\":\"mongod\",\n  \"app\":\"test\",\n  \"areaId\":\"test1\",\n  \"setId\":\"s2\",\n  \"auth\": true,\n  \"clusterRole\":\"shardsvr\",\n  \"dbConfig\":{\n    \"slowOpThresholdMs\":200,\n    \"cacheSizeGB\":1,\n    \"oplogSizeMB\":500,\n    \"destination\":\"file\"\n  }\n}"
	node2 = strings.Replace(node2, "{{ip}}", ip, -1)

	// node3
	node3 := "{\n  \"mediapkg\":{\n    \"pkg\":\"mongodb-linux-x86_64-3.4.20.tar.gz\",\n    \"pkg_md5\":\"e68d998d75df81b219e99795dec43ffb\"\n  },\n  \"ip\":\"{{ip}}\",\n  \"port\":27007,\n  \"dbVersion\":\"3.4.20\",\n  \"instanceType\":\"mongod\",\n  \"app\":\"test\",\n  \"areaId\":\"test1\",\n  \"setId\":\"s2\",\n  \"auth\": true,\n  \"clusterRole\":\"shardsvr\",\n  \"dbConfig\":{\n    \"slowOpThresholdMs\":200,\n    \"cacheSizeGB\":1,\n    \"oplogSizeMB\":500,\n    \"destination\":\"file\"\n  }\n}"
	node3 = strings.Replace(node3, "{{ip}}", ip, -1)

	node1MongodInstall := NewMongoDBInstall()
	node2MongodInstall := NewMongoDBInstall()
	node3MongodInstall := NewMongoDBInstall()

	node1Runtime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: node1,
	}
	node1Runtime.SetLogger()
	node2Runtime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: node2,
	}
	node2Runtime.SetLogger()
	node3Runtime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: node3,
	}
	node3Runtime.SetLogger()

	// 安装节点
	if err := node1MongodInstall.Init(node1Runtime); err != nil {
		fmt.Println(fmt.Sprintf("shard2 replicate install node1 init fail, error:%s", err))
		t.Errorf("shard2 replicate install node1 init fail, error:%s", err)
		return
	}
	if err := node1MongodInstall.Run(); err != nil {
		fmt.Println(fmt.Sprintf("shard2 replicate install node1 run fail, error:%s", err))
		t.Errorf("shard2 replicate install node1 run fail, error:%s", err)
		return
	}
	if err := node2MongodInstall.Init(node2Runtime); err != nil {
		fmt.Println(fmt.Sprintf("shard2 replicate install node2 init fail, error:%s", err))
		t.Errorf("shard2 replicate install node2 init fail, error:%s", err)
		return
	}
	if err := node2MongodInstall.Run(); err != nil {
		fmt.Println(fmt.Sprintf("shard2 replicate install node2 run fail, error:%s", err))
		t.Errorf("shard2 replicate install node2 run fail, error:%s", err)
		return
	}
	if err := node3MongodInstall.Init(node3Runtime); err != nil {
		fmt.Println(fmt.Sprintf("shard2 replicate install node3 init fail, error:%s", err))
		t.Errorf("shard2 replicate install node3 init fail, error:%s", err)
		return
	}
	if err := node3MongodInstall.Run(); err != nil {
		fmt.Println(fmt.Sprintf("shard2 replicate install node3 run fail, error:%s", err))
		t.Errorf("shard2 replicate install node3 run fail, error:%s", err)
		return
	}

	// 复制集初始化
	initReplicasetParam := "{\n  \"ip\":\"{{ip}}\",\n  \"port\":27005,\n  \"app\":\"test\",\n  \"areaId\":\"test1\",\n  \"setId\":\"s2\",\n  \"configSvr\":false,\n  \"ips\":[\n    \"{{ip}}:27005\",\n    \"{{ip}}:27006\",\n    \"{{ip}}:27007\"\n  ],\n  \"priority\":{\n    \"{{ip}}:27005\":1,\n    \"{{ip}}:27006\":1,\n    \"{{ip}}:27007\":0\n  },\n  \"hidden\":{\n    \"{{ip}}:27005\":false,\n    \"{{ip}}:27006\":false,\n    \"{{ip}}:27007\":true\n  }\n}"
	initReplicasetParam = strings.Replace(initReplicasetParam, "{{ip}}", ip, -1)
	initReplicasetRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: initReplicasetParam,
	}
	initReplicasetRuntime.SetLogger()
	initReplicaset := NewInitiateReplicaset()
	if err := initReplicaset.Init(initReplicasetRuntime); err != nil {
		fmt.Println(fmt.Sprintf("shard2 replicate install initReplicaset init fail, error:%s", err))
		t.Errorf("shard2 replicate install initReplicaset init fail, error:%s", err)
		return
	}
	if err := initReplicaset.Run(); err != nil {
		fmt.Println(fmt.Sprintf("shard2 replicate install initReplicaset run fail, error:%s", err))
		t.Errorf("shard2 replicate install initReplicaset run fail, error:%s", err)
		return
	}
	time.Sleep(time.Second * 3)
	// 创建管理员用户
	addAdminUserParam := "{\n  \"ip\":\"{{ip}}\",\n  \"port\":27005,\n  \"instanceType\":\"mongod\",\n  \"username\":\"dba\",\n  \"password\":\"dba\",\n  \"adminUsername\":\"\",\n  \"adminPassword\":\"\",\n  \"authDb\":\"admin\",\n  \"dbs\":[\n\n  ],\n  \"privileges\":[\n    \"root\"\n  ]\n}"
	addAdminUserParam = strings.Replace(addAdminUserParam, "{{ip}}", ip, -1)
	addAdminUserRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: addAdminUserParam,
	}
	addAdminUserRuntime.SetLogger()
	addAdminUser := NewAddUser()
	if err := addAdminUser.Init(addAdminUserRuntime); err != nil {
		fmt.Println(fmt.Sprintf("shard2 replicate install addAdminUser init fail, error:%s", err))
		t.Errorf("shard2 replicate install addAdminUser init fail, error:%s", err)
		return
	}
	if err := addAdminUser.Run(); err != nil {
		fmt.Println(fmt.Sprintf("shard2 replicate install addAdminUser run fail, error:%s", err))
		t.Errorf("shard2 replicate install addAdminUser run fail, error:%s", err)
		return
	}
}

// TestConfigDB 安装ConfigDB测试
func TestConfigDB(t *testing.T) {
	// 设置环境变量
	err := consts.SetMongoDataDir("")
	if err != nil {
		fmt.Println(fmt.Sprintf("configdb install SetMongoData fail, error:%s", err))
		t.Errorf("configdb install SetMongoData fail, error:%s", err)
		return
	}
	err = consts.SetMongoBackupDir("")
	if err != nil {
		fmt.Println(fmt.Sprintf("configdb install SetMongoBackup fail, error:%s", err))
		t.Errorf("configdb install SetMongoBackup fail, error:%s", err)
		return
	}

	err = consts.SetProcessUser("")
	if err != nil {
		fmt.Println(fmt.Sprintf("configdb install SetProcessUser fail, error:%s", err))
		t.Errorf("configdb install SetProcessUser fail, error:%s", err)
		return
	}
	err = consts.SetProcessUserGroup("")
	if err != nil {
		fmt.Println(fmt.Sprintf("configdb install SetProcessUserGroup fail, error:%s", err))
		t.Errorf("configdb install SetProcessUserGroup fail, error:%s", err)
		return
	}

	// 初始化节点
	osSysInitParam := "{\n\"user\":\"mysql\",\n\"password\":\"Qwe123d\"\n}"
	osSysInit := &atomsys.OsMongoInit{}
	osSysInitRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: osSysInitParam,
	}
	osSysInitRuntime.SetLogger()
	if err := osSysInit.Init(osSysInitRuntime); err != nil {
		fmt.Println(fmt.Sprintf("configdb replicate install osSysInit init fail, error:%s", err))
		t.Errorf("configdb replicate install osSysInit init fail, error:%s", err)
		return
	}
	if err := osSysInit.Run(); err != nil {
		fmt.Println(fmt.Sprintf("configdb replicate install osSysInit run fail, error:%s", err))
		t.Errorf("configdb replicate install osSysInit run fail, error:%s", err)
		return
	}

	// 获取本机IP地址
	var ip string
	addrs, _ := net.InterfaceAddrs()
	for _, addr := range addrs {
		if !strings.Contains(addr.String(), "127.0.0.1") {
			ip = strings.Split(addr.String(), "/")[0]
			break
		}
	}

	// node1
	node1 := "{\n  \"mediapkg\":{\n    \"pkg\":\"mongodb-linux-x86_64-3.4.20.tar.gz\",\n    \"pkg_md5\":\"e68d998d75df81b219e99795dec43ffb\"\n  },\n  \"ip\":\"{{ip}}\",\n  \"port\":27020,\n  \"dbVersion\":\"3.4.20\",\n  \"instanceType\":\"mongod\",\n  \"app\":\"test\",\n  \"areaId\":\"test1\",\n  \"setId\":\"conf\",\n  \"auth\": true,\n  \"clusterRole\":\"configsvr\",\n  \"dbConfig\":{\n    \"slowOpThresholdMs\":200,\n    \"cacheSizeGB\":1,\n    \"oplogSizeMB\":500,\n    \"destination\":\"file\"\n  }\n}"
	node1 = strings.Replace(node1, "{{ip}}", ip, -1)

	// node2
	node2 := "{\n  \"mediapkg\":{\n    \"pkg\":\"mongodb-linux-x86_64-3.4.20.tar.gz\",\n    \"pkg_md5\":\"e68d998d75df81b219e99795dec43ffb\"\n  },\n  \"ip\":\"{{ip}}\",\n  \"port\":27021,\n  \"dbVersion\":\"3.4.20\",\n  \"instanceType\":\"mongod\",\n  \"app\":\"test\",\n  \"areaId\":\"test1\",\n  \"setId\":\"conf\",\n  \"auth\": true,\n  \"clusterRole\":\"configsvr\",\n  \"dbConfig\":{\n    \"slowOpThresholdMs\":200,\n    \"cacheSizeGB\":1,\n    \"oplogSizeMB\":500,\n    \"destination\":\"file\"\n  }\n}"
	node2 = strings.Replace(node2, "{{ip}}", ip, -1)

	// node3
	node3 := "{\n  \"mediapkg\":{\n    \"pkg\":\"mongodb-linux-x86_64-3.4.20.tar.gz\",\n    \"pkg_md5\":\"e68d998d75df81b219e99795dec43ffb\"\n  },\n  \"ip\":\"{{ip}}\",\n  \"port\":27022,\n  \"dbVersion\":\"3.4.20\",\n  \"instanceType\":\"mongod\",\n  \"app\":\"test\",\n  \"areaId\":\"test1\",\n  \"setId\":\"conf\",\n  \"auth\": true,\n  \"clusterRole\":\"configsvr\",\n  \"dbConfig\":{\n    \"slowOpThresholdMs\":200,\n    \"cacheSizeGB\":1,\n    \"oplogSizeMB\":500,\n    \"destination\":\"file\"\n  }\n}"
	node3 = strings.Replace(node3, "{{ip}}", ip, -1)
	// node4
	node4 := "{\n  \"mediapkg\":{\n    \"pkg\":\"mongodb-linux-x86_64-3.4.20.tar.gz\",\n    \"pkg_md5\":\"e68d998d75df81b219e99795dec43ffb\"\n  },\n  \"ip\":\"{{ip}}\",\n  \"port\":27004,\n  \"dbVersion\":\"3.4.20\",\n  \"instanceType\":\"mongod\",\n  \"app\":\"test\",\n  \"areaId\":\"test1\",\n  \"setId\":\"conf\",\n  \"auth\": true,\n  \"clusterRole\":\"configsvr\",\n  \"dbConfig\":{\n    \"slowOpThresholdMs\":200,\n    \"cacheSizeGB\":1,\n    \"oplogSizeMB\":500,\n    \"destination\":\"file\"\n  }\n}"
	node4 = strings.Replace(node4, "{{ip}}", ip, -1)

	node1MongodInstall := NewMongoDBInstall()
	node2MongodInstall := NewMongoDBInstall()
	node3MongodInstall := NewMongoDBInstall()
	node4MongodInstall := NewMongoDBInstall()

	node1Runtime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: node1,
	}
	node1Runtime.SetLogger()
	node2Runtime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: node2,
	}
	node2Runtime.SetLogger()
	node3Runtime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: node3,
	}
	node3Runtime.SetLogger()
	node4Runtime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: node4,
	}
	node4Runtime.SetLogger()

	// 安装节点
	if err := node1MongodInstall.Init(node1Runtime); err != nil {
		fmt.Println(fmt.Sprintf("configdb replicate install node1 init fail, error:%s", err))
		t.Errorf("configdb replicate install node1 init fail, error:%s", err)
		return
	}
	if err := node1MongodInstall.Run(); err != nil {
		fmt.Println(fmt.Sprintf("configdb replicate install node1 run fail, error:%s", err))
		t.Errorf("configdb replicate install node1 run fail, error:%s", err)
		return
	}
	if err := node2MongodInstall.Init(node2Runtime); err != nil {
		fmt.Println(fmt.Sprintf("configdb replicate install node2 init fail, error:%s", err))
		t.Errorf("configdb replicate install node2 init fail, error:%s", err)
		return
	}
	if err := node2MongodInstall.Run(); err != nil {
		fmt.Println(fmt.Sprintf("configdb replicate install node2 run fail, error:%s", err))
		t.Errorf("configdb replicate install node2 run fail, error:%s", err)
		return
	}
	if err := node3MongodInstall.Init(node3Runtime); err != nil {
		fmt.Println(fmt.Sprintf("configdb replicate install node3 init fail, error:%s", err))
		t.Errorf("configdb replicate install node3 init fail, error:%s", err)
		return
	}
	if err := node3MongodInstall.Run(); err != nil {
		fmt.Println(fmt.Sprintf("configdb replicate install node3 run fail, error:%s", err))
		t.Errorf("configdb replicate install node3 run fail, error:%s", err)
		return
	}
	if err := node4MongodInstall.Init(node4Runtime); err != nil {
		fmt.Println(fmt.Sprintf("configdb replicate install node4 init fail, error:%s", err))
		t.Errorf("configdb replicate install node4 init fail, error:%s", err)
		return
	}
	if err := node4MongodInstall.Run(); err != nil {
		fmt.Println(fmt.Sprintf("configdb replicate install node4 run fail, error:%s", err))
		t.Errorf("configdb replicate install node4 run fail, error:%s", err)
		return
	}

	// 复制集初始化
	initReplicasetParam := "{\n  \"ip\":\"{{ip}}\",\n  \"port\":27020,\n  \"app\":\"test\",\n  \"areaId\":\"test1\",\n  \"setId\":\"conf\",\n  \"configSvr\":true,\n  \"ips\":[\n    \"{{ip}}:27020\",\n    \"{{ip}}:27021\",\n    \"{{ip}}:27022\"\n  ],\n  \"priority\":{\n    \"{{ip}}:27020\":1,\n    \"{{ip}}:27021\":1,\n    \"{{ip}}:27022\":0\n  },\n  \"hidden\":{\n    \"{{ip}}:27020\":false,\n    \"{{ip}}:27021\":false,\n    \"{{ip}}:27022\":true\n  }\n}"
	initReplicasetParam = strings.Replace(initReplicasetParam, "{{ip}}", ip, -1)
	initReplicasetRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: initReplicasetParam,
	}
	initReplicasetRuntime.SetLogger()
	initReplicaset := NewInitiateReplicaset()
	if err := initReplicaset.Init(initReplicasetRuntime); err != nil {
		fmt.Println(fmt.Sprintf("configdb replicate install initReplicaset init fail, error:%s", err))
		t.Errorf("configdb replicate install initReplicaset init fail, error:%s", err)
		return
	}
	if err := initReplicaset.Run(); err != nil {
		fmt.Println(fmt.Sprintf("configdb replicate install initReplicaset run fail, error:%s", err))
		t.Errorf("configdb replicate install initReplicaset run fail, error:%s", err)
		return
	}
	time.Sleep(time.Second * 3)
	// 创建管理员用户
	addAdminUserParam := "{\n  \"ip\":\"{{ip}}\",\n  \"port\":27020,\n  \"instanceType\":\"mongod\",\n  \"username\":\"dba\",\n  \"password\":\"dba\",\n  \"adminUsername\":\"\",\n  \"adminPassword\":\"\",\n  \"authDb\":\"admin\",\n  \"dbs\":[\n\n  ],\n  \"privileges\":[\n    \"root\"\n  ]\n}"
	addAdminUserParam = strings.Replace(addAdminUserParam, "{{ip}}", ip, -1)
	addAdminUserRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: addAdminUserParam,
	}
	addAdminUserRuntime.SetLogger()
	addAdminUser := NewAddUser()
	if err := addAdminUser.Init(addAdminUserRuntime); err != nil {
		fmt.Println(fmt.Sprintf("configdb replicate install addAdminUser init fail, error:%s", err))
		t.Errorf("configdb replicate install addAdminUser init fail, error:%s", err)
		return
	}
	if err := addAdminUser.Run(); err != nil {
		fmt.Println(fmt.Sprintf("configdb replicate install addAdminUser run fail, error:%s", err))
		t.Errorf("configdb replicate install addAdminUser run fail, error:%s", err)
		return
	}
}

// TestMongoS 安装mongos测试
func TestMongoS(t *testing.T) {
	// 设置环境变量
	err := consts.SetMongoDataDir("")
	if err != nil {
		fmt.Println(fmt.Sprintf("mongos install SetMongoData fail, error:%s", err))
		t.Errorf("mongos install SetMongoData fail, error:%s", err)
		return
	}
	err = consts.SetMongoBackupDir("")
	if err != nil {
		fmt.Println(fmt.Sprintf("mongos install SetMongoBackup fail, error:%s", err))
		t.Errorf("mongos install SetMongoBackup fail, error:%s", err)
		return
	}

	err = consts.SetProcessUser("")
	if err != nil {
		fmt.Println(fmt.Sprintf("mongos install SetProcessUser fail, error:%s", err))
		t.Errorf("mongos install SetProcessUser fail, error:%s", err)
		return
	}
	err = consts.SetProcessUserGroup("")
	if err != nil {
		fmt.Println(fmt.Sprintf("mongos install SetProcessUserGroup fail, error:%s", err))
		t.Errorf("mongos install SetProcessUserGroup fail, error:%s", err)
		return
	}

	// 初始化节点
	osSysInitParam := "{\n\"user\":\"mysql\",\n\"password\":\"Qwe123d\"\n}"
	osSysInit := &atomsys.OsMongoInit{}
	osSysInitRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: osSysInitParam,
	}
	osSysInitRuntime.SetLogger()
	if err := osSysInit.Init(osSysInitRuntime); err != nil {
		fmt.Println(fmt.Sprintf("mongos install osSysInit init fail, error:%s", err))
		t.Errorf("mongos install osSysInit init fail, error:%s", err)
		return
	}
	if err := osSysInit.Run(); err != nil {
		fmt.Println(fmt.Sprintf("mongos install osSysInit run fail, error:%s", err))
		t.Errorf("monogs install osSysInit run fail, error:%s", err)
		return
	}

	// 获取本机IP地址
	var ip string
	addrs, _ := net.InterfaceAddrs()
	for _, addr := range addrs {
		if !strings.Contains(addr.String(), "127.0.0.1") {
			ip = strings.Split(addr.String(), "/")[0]
			break
		}
	}
	mongos1Param := "{\n  \"mediapkg\":{\n    \"pkg\":\"mongodb-linux-x86_64-3.4.20.tar.gz\",\n    \"pkg_md5\":\"e68d998d75df81b219e99795dec43ffb\"\n  },\n  \"ip\":\"{{ip}}\",\n  \"port\":27030,\n  \"dbVersion\":\"3.4.20\",\n  \"instanceType\":\"mongos\",\n  \"app\":\"test\",\n  \"areaId\":\"test1\",\n  \"auth\": true,\n  \"configDB\":[\"{{ip}}:27020\",\"{{ip}}:27021\",\"{{ip}}:27022\"],\n  \"dbConfig\":{\n    \"slowOpThresholdMs\":200,\n    \"destination\":\"file\"\n  }\n}"
	mongos2Param := "{\n  \"mediapkg\":{\n    \"pkg\":\"mongodb-linux-x86_64-3.4.20.tar.gz\",\n    \"pkg_md5\":\"e68d998d75df81b219e99795dec43ffb\"\n  },\n  \"ip\":\"{{ip}}\",\n  \"port\":27031,\n  \"dbVersion\":\"3.4.20\",\n  \"instanceType\":\"mongos\",\n  \"app\":\"test\",\n  \"areaId\":\"test1\",\n  \"auth\": true,\n  \"configDB\":[\"{{ip}}:27020\",\"{{ip}}:27021\",\"{{ip}}:27022\"],\n  \"dbConfig\":{\n    \"slowOpThresholdMs\":200,\n    \"destination\":\"file\"\n  }\n}"
	mongos1Param = strings.Replace(mongos1Param, "{{ip}}", ip, -1)
	mongos2Param = strings.Replace(mongos2Param, "{{ip}}", ip, -1)

	mongos1MongoSInstall := NewMongoSInstall()
	mongos2MongoSInstall := NewMongoSInstall()

	mongos1Runtime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: mongos1Param,
	}
	mongos1Runtime.SetLogger()
	mongos2Runtime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: mongos2Param,
	}
	mongos2Runtime.SetLogger()

	// 安装mongos
	if err := mongos1MongoSInstall.Init(mongos1Runtime); err != nil {
		fmt.Println(fmt.Sprintf("mongos1 install init fail, error:%s", err))
		t.Errorf("mongos1 install node1 init fail, error:%s", err)
		return
	}
	if err := mongos1MongoSInstall.Run(); err != nil {
		fmt.Println(fmt.Sprintf("mongos1 install node1 run fail, error:%s", err))
		t.Errorf("mongos1 install node1 run fail, error:%s", err)
		return
	}
	if err := mongos2MongoSInstall.Init(mongos2Runtime); err != nil {
		fmt.Println(fmt.Sprintf("mongos2 install init fail, error:%s", err))
		t.Errorf("mongos3 install init fail, error:%s", err)
		return
	}
	if err := mongos2MongoSInstall.Run(); err != nil {
		fmt.Println(fmt.Sprintf("mongos2 install node1 run fail, error:%s", err))
		t.Errorf("mongos2 install run fail, error:%s", err)
		return
	}

}

func TestCluster(t *testing.T) {
	// 设置环境变量
	err := consts.SetMongoDataDir("")
	if err != nil {
		fmt.Println(fmt.Sprintf("cluster SetMongoData fail, error:%s", err))
		t.Errorf("cluster SetMongoData fail, error:%s", err)
		return
	}
	err = consts.SetMongoBackupDir("")
	if err != nil {
		fmt.Println(fmt.Sprintf("cluster SetMongoBackup fail, error:%s", err))
		t.Errorf("cluster SetMongoBackup fail, error:%s", err)
		return
	}

	err = consts.SetProcessUser("")
	if err != nil {
		fmt.Println(fmt.Sprintf("cluster SetProcessUser fail, error:%s", err))
		t.Errorf("cluster SetProcessUser fail, error:%s", err)
		return
	}
	err = consts.SetProcessUserGroup("")
	if err != nil {
		fmt.Println(fmt.Sprintf("cluster SetProcessUserGroup fail, error:%s", err))
		t.Errorf("cluster SetProcessUserGroup fail, error:%s", err)
		return
	}

	// 初始化节点
	osSysInitParam := "{\n\"user\":\"mysql\",\n\"password\":\"Qwe123d\"\n}"
	osSysInit := &atomsys.OsMongoInit{}
	osSysInitRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: osSysInitParam,
	}
	osSysInitRuntime.SetLogger()
	if err := osSysInit.Init(osSysInitRuntime); err != nil {
		fmt.Println(fmt.Sprintf("cluster osSysInit init fail, error:%s", err))
		t.Errorf("cluster osSysInit init fail, error:%s", err)
		return
	}
	if err := osSysInit.Run(); err != nil {
		fmt.Println(fmt.Sprintf("cluster osSysInit run fail, error:%s", err))
		t.Errorf("cluster osSysInit run fail, error:%s", err)
		return
	}

	// 获取本机IP地址
	var ip string
	addrs, _ := net.InterfaceAddrs()
	for _, addr := range addrs {
		if !strings.Contains(addr.String(), "127.0.0.1") {
			ip = strings.Split(addr.String(), "/")[0]
			break
		}
	}

	// cluster添加shard
	addShardParam := "{\n  \"ip\":\"{{ip}}\",\n  \"port\":27030,\n  \"adminUsername\":\"dba\",\n  \"adminPassword\":\"dba\",\n  \"shard\":{\n    \"test-test1-s1\":\"{{ip}}:27001,{{ip}}:27002\",\n    \"test-test1-s2\":\"{{ip}}:27005,{{ip}}:27006\"\n  }\n}"
	addShardParam = strings.Replace(addShardParam, "{{ip}}", ip, -1)
	addShard := NewAddShardToCluster()

	addShardRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: addShardParam,
	}
	addShardRuntime.SetLogger()

	if err := addShard.Init(addShardRuntime); err != nil {
		fmt.Println(fmt.Sprintf("cluster addShard init fail, error:%s", err))
		t.Errorf("cluster addShard init fail, error:%s", err)
		return
	}
	if err := addShard.Run(); err != nil {
		fmt.Println(fmt.Sprintf("cluster addShard run fail, error:%s", err))
		t.Errorf("cluster addShard run fail, error:%s", err)
		return
	}

	// 创建业务用户
	addUserParam := "{\n  \"ip\":\"{{ip}}\",\n  \"port\":27030,\n  \"instanceType\":\"mongos\",\n  \"username\":\"test\",\n  \"password\":\"test\",\n  \"adminUsername\":\"dba\",\n  \"adminPassword\":\"dba\",\n  \"authDb\":\"admin\",\n  \"dbs\":[\n\n  ],\n  \"privileges\":[\n    \"readWriteAnyDatabase\"\n  ]\n}"
	addUserParam = strings.Replace(addUserParam, "{{ip}}", ip, -1)
	addUserRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: addUserParam,
	}
	addUserRuntime.SetLogger()
	addUser := NewAddUser()
	if err := addUser.Init(addUserRuntime); err != nil {
		fmt.Println(fmt.Sprintf("cluster addUser init fail, error:%s", err))
		t.Errorf("cluster addUser init fail, error:%s", err)
		return
	}
	if err := addUser.Run(); err != nil {
		fmt.Println(fmt.Sprintf("cluster addUser run fail, error:%s", err))
		t.Errorf("cluster addUser run fail, error:%s", err)
		return
	}

	// 删除业务用户
	delUserParam := "{\n  \"ip\":\"{{ip}}\",\n  \"port\":27030,\n  \"instanceType\":\"mongos\",\n  \"adminUsername\":\"dba\",\n  \"adminPassword\":\"dba\",\n  \"username\":\"test\",\n  \"authDb\":\"admin\"\n}"
	delUserParam = strings.Replace(delUserParam, "{{ip}}", ip, -1)
	delUserRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: delUserParam,
	}
	delUserRuntime.SetLogger()
	delUser := NewDelUser()
	if err := delUser.Init(delUserRuntime); err != nil {
		fmt.Println(fmt.Sprintf("cluster delUser init fail, error:%s", err))
		t.Errorf("cluster delUser init fail, error:%s", err)
		return
	}
	if err := delUser.Run(); err != nil {
		fmt.Println(fmt.Sprintf("cluster delUser run fail, error:%s", err))
		t.Errorf("cluster delUser run fail, error:%s", err)
		return
	}

	// 执行脚本
	execScriptParam := "{\n  \"ip\":\"{{ip}}\",\n  \"port\":27030,\n  \"script\":\"var mongo = db;\\nmongo.getSisterDB('admin').runCommand({listDatabases:1}).databases.forEach (function (x) { print(x.name)});\\n\",\n  \"type\":\"cluster\",\n  \"secondary\": false,\n  \"adminUsername\":\"dba\",\n  \"adminPassword\":\"dba\",\n  \"repoUrl\":\"\",\n  \"repoUsername\":\"\",\n  \"repoToken\":\"\",\n  \"repoProject\":\"\",\n  \"repoRepo\":\"\",\n  \"repoPath\":\"\"\n}"
	execScriptParam = strings.Replace(execScriptParam, "{{ip}}", ip, -1)
	execScriptRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: execScriptParam,
	}
	execScriptRuntime.SetLogger()
	execScript := NewExecScript()
	if err := execScript.Init(execScriptRuntime); err != nil {
		fmt.Println(fmt.Sprintf("cluster execScript init fail, error:%s", err))
		t.Errorf("cluster execScript init fail, error:%s", err)
		return
	}
	if err := execScript.Run(); err != nil {
		fmt.Println(fmt.Sprintf("cluster execScript run fail, error:%s", err))
		t.Errorf("cluster execScript run fail, error:%s", err)
		return
	}

	// 重启mongod
	restartParam := "{\n  \"ip\":\"{{ip}}\",\n  \"port\":27005,\n  \"instanceType\":\"mongod\",\n  \"singleNodeInstallRestart\":false,  \n  \"auth\":true,\n  \"cacheSizeGB\": 2,\n  \"mongoSConfDbOld\":\"\",\n  \"MongoSConfDbNew\":\"\",\n  \"adminUsername\":\"dba\",\n  \"adminPassword\":\"dba\"\n}"
	restartParam = strings.Replace(restartParam, "{{ip}}", ip, -1)
	restartRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: restartParam,
	}
	restartRuntime.SetLogger()
	restart := NewMongoRestart()
	if err := restart.Init(restartRuntime); err != nil {
		fmt.Println(fmt.Sprintf("cluster shard mongod restart init fail, error:%s", err))
		t.Errorf("cluster shard mongod restart init fail, error:%s", err)
		return
	}
	if err := restart.Run(); err != nil {
		fmt.Println(fmt.Sprintf("cluster shard mongod restart run fail, error:%s", err))
		t.Errorf("cluster shard mongod restart run fail, error:%s", err)
		return
	}

	time.Sleep(time.Second * 3)
	// 替换config节点
	replaceParam := "{\n  \"ip\":\"{{ip}}\",\n  \"port\":27020,\n  \"sourceIP\":\"{{ip}}\",\n  \"sourcePort\":27020,\n  \"sourceDown\":false,\n  \"adminUsername\":\"dba\",\n  \"adminPassword\":\"dba\",\n  \"targetIP\":\"{{ip}}\",\n  \"targetPort\":27004,\n  \"targetPriority\":\"\",\n  \"targetHidden\":\"\"\n}"
	replaceParam = strings.Replace(replaceParam, "{{ip}}", ip, -1)
	replaceRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: replaceParam,
	}
	replaceRuntime.SetLogger()
	replace := NewMongoDReplace()
	if err := replace.Init(replaceRuntime); err != nil {
		fmt.Println(fmt.Sprintf("cluster replace config mongod init fail, error:%s", err))
		t.Errorf("cluster replace config mongod init fail, error:%s", err)
		return
	}
	if err := replace.Run(); err != nil {
		fmt.Println(fmt.Sprintf("cluster replace config mongod run fail, error:%s", err))
		t.Errorf("cluster replace config mongod run fail, error:%s", err)
		return
	}

	// 重启mongos
	restart1Param := "{\n  \"ip\":\"{{ip}}\",\n  \"port\":27030,\n  \"instanceType\":\"mongos\",\n  \"singleNodeInstallRestart\":false,  \n  \"auth\":true,\n  \"cacheSizeGB\": 0,\n  \"mongoSConfDbOld\":\"{{ip}}:27020\",\n  \"MongoSConfDbNew\":\"{{ip}}:27004\",\n  \"adminUsername\":\"\",\n  \"adminPassword\":\"\"\n}"
	restart1Param = strings.Replace(restart1Param, "{{ip}}", ip, -1)
	restart1Runtime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: restart1Param,
	}
	restart1Runtime.SetLogger()
	restart1 := NewMongoRestart()
	if err := restart1.Init(restart1Runtime); err != nil {
		fmt.Println(fmt.Sprintf("cluster mongos port:%d restart init fail, error:%s", 27030, err))
		t.Errorf("cluster mongos port:%d restart init fail, error:%s", 27030, err)
		return
	}
	if err := restart1.Run(); err != nil {
		fmt.Println(fmt.Sprintf("cluster mongos port:%d restart run fail, error:%s", 27030, err))
		t.Errorf("cluster mongos restart port:%d run fail, error:%s", 27030, err)
		return
	}

	restart2Param := "{\n  \"ip\":\"{{ip}}\",\n  \"port\":27031,\n  \"instanceType\":\"mongos\",\n  \"singleNodeInstallRestart\":false,  \n  \"auth\":true,\n  \"cacheSizeGB\": 0,\n  \"mongoSConfDbOld\":\"{{ip}}:27020\",\n  \"MongoSConfDbNew\":\"{{ip}}:27004\",\n  \"adminUsername\":\"\",\n  \"adminPassword\":\"\"\n}"
	restart2Param = strings.Replace(restart2Param, "{{ip}}", ip, -1)
	restart2Runtime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: restart2Param,
	}
	restart2Runtime.SetLogger()
	restart2 := NewMongoRestart()
	if err := restart2.Init(restart2Runtime); err != nil {
		fmt.Println(fmt.Sprintf("cluster mongos port:%d restart init fail, error:%s", 27031, err))
		t.Errorf("cluster mongos port:%d restart init fail, error:%s", 27031, err)
		return
	}
	if err := restart2.Run(); err != nil {
		fmt.Println(fmt.Sprintf("cluster mongos port:%d restart run fail, error:%s", 27031, err))
		t.Errorf("cluster mongos restart port:%d run fail, error:%s", 27031, err)
		return
	}

	time.Sleep(time.Second * 3)
	// 下架mongos
	for _, i := range []int{27030, 27031} {
		deinstallParam := fmt.Sprintf("{\n    \"ip\":\"{{ip}}\",\n    \"port\":%d,\n    \"app\":\"test\",\n    \"areaId\":\"test1\",\n    \"nodeInfo\":[\n        \"{{ip}}\"\n    ],\n    \"instanceType\":\"mongos\"\n}", i)
		deinstallParam = strings.Replace(deinstallParam, "{{ip}}", ip, -1)
		deinstallRuntime := &jobruntime.JobGenericRuntime{
			PayloadDecoded: deinstallParam,
		}
		deinstallRuntime.SetLogger()
		deinstal := NewDeInstall()
		if err := deinstal.Init(deinstallRuntime); err != nil {
			fmt.Println(fmt.Sprintf("cluster deinstal mongos port:%d init fail, error:%s", i, err))
			t.Errorf("cluster deinstal mongos port:%d init fail, error:%s", i, err)
			return
		}
		if err := deinstal.Run(); err != nil {
			fmt.Println(fmt.Sprintf("cluster deinstal mongos deinstal port:%d run fail, error:%s", i, err))
			t.Errorf("cluster deinstal mongos port:%d run fail, error:%s", i, err)
			return
		}
	}

	time.Sleep(time.Second * 2)
	// 下架shard
	for _, i := range []int{27001, 27002, 27003, 27005, 27006, 27007} {
		deinstallParam := fmt.Sprintf("{\n    \"ip\":\"{{ip}}\",\n    \"port\":%d,\n    \"app\":\"test\",\n    \"areaId\":\"test1\",\n    \"nodeInfo\":[\n        \"{{ip}}\"\n    ],\n    \"instanceType\":\"mongod\"\n}", i)
		deinstallParam = strings.Replace(deinstallParam, "{{ip}}", ip, -1)
		deinstallRuntime := &jobruntime.JobGenericRuntime{
			PayloadDecoded: deinstallParam,
		}
		deinstallRuntime.SetLogger()
		deinstal := NewDeInstall()
		if err := deinstal.Init(deinstallRuntime); err != nil {
			fmt.Println(fmt.Sprintf("cluster deinstal shard mongod port:%d init fail, error:%s", i, err))
			t.Errorf("cluster deinstal shard mongod port:%d init fail, error:%s", i, err)
			return
		}
		if err := deinstal.Run(); err != nil {
			fmt.Println(fmt.Sprintf("cluster deinstal shard mongod deinstal port:%d run fail, error:%s", i, err))
			t.Errorf("cluster deinstal shard mongod port:%d run fail, error:%s", i, err)
			return
		}
	}

	time.Sleep(time.Second * 2)
	// 下架configdb
	for _, i := range []int{27004, 27021, 27022} {
		deinstallParam := fmt.Sprintf("{\n    \"ip\":\"{{ip}}\",\n    \"port\":%d,\n    \"app\":\"test\",\n    \"areaId\":\"test1\",\n    \"nodeInfo\":[\n        \"{{ip}}\"\n    ],\n    \"instanceType\":\"mongod\"\n}", i)
		deinstallParam = strings.Replace(deinstallParam, "{{ip}}", ip, -1)
		deinstallRuntime := &jobruntime.JobGenericRuntime{
			PayloadDecoded: deinstallParam,
		}
		deinstallRuntime.SetLogger()
		deinstal := NewDeInstall()
		if err := deinstal.Init(deinstallRuntime); err != nil {
			fmt.Println(fmt.Sprintf("cluster deinstal configdb mongod port:%d init fail, error:%s", i, err))
			t.Errorf("cluster deinstal configdb mongod port:%d init fail, error:%s", i, err)
			return
		}
		if err := deinstal.Run(); err != nil {
			fmt.Println(fmt.Sprintf("cluster deinstal configdb mongod deinstal port:%d run fail, error:%s", i, err))
			t.Errorf("cluster deinstal configdb mongod port:%d run fail, error:%s", i, err)
			return
		}
	}

	// 删除相关目录
	dbData := path.Join(consts.GetMongoDataDir(), "mongodata")
	dbLog := path.Join(consts.GetMongoBackupDir(), "mongolog")
	softInstall := path.Join(consts.UsrLocal, "mongodb")
	cmd := fmt.Sprintf("rm -rf %s;rm -rf %s;rm -rf %s", dbData, dbLog, softInstall)
	if _, err = util.RunBashCmd(cmd, "", nil, 10*time.Second); err != nil {
		fmt.Println(fmt.Sprintf("delete directories fail, error:%s", err))
		t.Errorf("delete directories fail, error:%s", err)
	}

}
