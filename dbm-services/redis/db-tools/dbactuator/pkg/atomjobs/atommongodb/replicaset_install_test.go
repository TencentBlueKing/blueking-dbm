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

// TestReplicaset 复制集安装及相关操作测试
func TestReplicaset(t *testing.T) {
	// 设置环境变量
	err := consts.SetMongoDataDir("")
	if err != nil {
		fmt.Println(fmt.Sprintf("replicate install SetMongoData fail, error:%s", err))
		t.Errorf("replicate install SetMongoData fail, error:%s", err)
		return
	}
	err = consts.SetMongoBackupDir("")
	if err != nil {
		fmt.Println(fmt.Sprintf("replicate install SetMongoBackup fail, error:%s", err))
		t.Errorf("replicate install SetMongoBackup fail, error:%s", err)
		return
	}

	err = consts.SetProcessUser("")
	if err != nil {
		fmt.Println(fmt.Sprintf("replicate install SetProcessUser fail, error:%s", err))
		t.Errorf("replicate install SetProcessUser fail, error:%s", err)
		return
	}
	err = consts.SetProcessUserGroup("")
	if err != nil {
		fmt.Println(fmt.Sprintf("replicate install SetProcessUserGroup fail, error:%s", err))
		t.Errorf("replicate install SetProcessUserGroup fail, error:%s", err)
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
		fmt.Println(fmt.Sprintf("replicate install osSysInit init fail, error:%s", err))
		t.Errorf("replicate install osSysInit init fail, error:%s", err)
		return
	}
	if err := osSysInit.Run(); err != nil {
		fmt.Println(fmt.Sprintf("replicate install osSysInit run fail, error:%s", err))
		t.Errorf("replicate install osSysInit run fail, error:%s", err)
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
	node1 := "{\n  \"mediapkg\":{\n    \"pkg\":\"mongodb-linux-x86_64-3.4.20.tar.gz\",\n    \"pkg_md5\":\"e68d998d75df81b219e99795dec43ffb\"\n  },\n  \"ip\":\"{{ip}}\",\n  \"port\":27001,\n  \"dbVersion\":\"3.4.20\",\n  \"instanceType\":\"mongod\",\n  \"app\":\"test\",\n  \"areaId\":\"test1\",\n  \"setId\":\"s1\",\n  \"auth\": true,\n  \"clusterRole\":\"\",\n  \"dbConfig\":{\n    \"slowOpThresholdMs\":200,\n    \"cacheSizeGB\":1,\n    \"oplogSizeMB\":500,\n    \"destination\":\"file\"\n  }\n}"
	node1 = strings.Replace(node1, "{{ip}}", ip, -1)

	// node2
	node2 := "{\n  \"mediapkg\":{\n    \"pkg\":\"mongodb-linux-x86_64-3.4.20.tar.gz\",\n    \"pkg_md5\":\"e68d998d75df81b219e99795dec43ffb\"\n  },\n  \"ip\":\"{{ip}}\",\n  \"port\":27002,\n  \"dbVersion\":\"3.4.20\",\n  \"instanceType\":\"mongod\",\n  \"app\":\"test\",\n  \"areaId\":\"test1\",\n  \"setId\":\"s1\",\n  \"auth\": true,\n  \"clusterRole\":\"\",\n  \"dbConfig\":{\n    \"slowOpThresholdMs\":200,\n    \"cacheSizeGB\":1,\n    \"oplogSizeMB\":500,\n    \"destination\":\"file\"\n  }\n}"
	node2 = strings.Replace(node2, "{{ip}}", ip, -1)

	// node3
	node3 := "{\n  \"mediapkg\":{\n    \"pkg\":\"mongodb-linux-x86_64-3.4.20.tar.gz\",\n    \"pkg_md5\":\"e68d998d75df81b219e99795dec43ffb\"\n  },\n  \"ip\":\"{{ip}}\",\n  \"port\":27003,\n  \"dbVersion\":\"3.4.20\",\n  \"instanceType\":\"mongod\",\n  \"app\":\"test\",\n  \"areaId\":\"test1\",\n  \"setId\":\"s1\",\n  \"auth\": true,\n  \"clusterRole\":\"\",\n  \"dbConfig\":{\n    \"slowOpThresholdMs\":200,\n    \"cacheSizeGB\":1,\n    \"oplogSizeMB\":500,\n    \"destination\":\"file\"\n  }\n}"
	node3 = strings.Replace(node3, "{{ip}}", ip, -1)

	// node4
	node4 := "{\n  \"mediapkg\":{\n    \"pkg\":\"mongodb-linux-x86_64-3.4.20.tar.gz\",\n    \"pkg_md5\":\"e68d998d75df81b219e99795dec43ffb\"\n  },\n  \"ip\":\"{{ip}}\",\n  \"port\":27004,\n  \"dbVersion\":\"3.4.20\",\n  \"instanceType\":\"mongod\",\n  \"app\":\"test\",\n  \"areaId\":\"test1\",\n  \"setId\":\"s1\",\n  \"auth\": true,\n  \"clusterRole\":\"\",\n  \"dbConfig\":{\n    \"slowOpThresholdMs\":200,\n    \"cacheSizeGB\":1,\n    \"oplogSizeMB\":500,\n    \"destination\":\"file\"\n  }\n}"
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
		fmt.Println(fmt.Sprintf("replicate install node1 init fail, error:%s", err))
		t.Errorf("replicate install node1 init fail, error:%s", err)
		return
	}
	if err := node1MongodInstall.Run(); err != nil {
		fmt.Println(fmt.Sprintf("replicate install node1 run fail, error:%s", err))
		t.Errorf("replicate install node1 run fail, error:%s", err)
		return
	}
	if err := node2MongodInstall.Init(node2Runtime); err != nil {
		fmt.Println(fmt.Sprintf("replicate install node2 init fail, error:%s", err))
		t.Errorf("replicate install node2 init fail, error:%s", err)
		return
	}
	if err := node2MongodInstall.Run(); err != nil {
		fmt.Println(fmt.Sprintf("replicate install node2 run fail, error:%s", err))
		t.Errorf("replicate install node2 run fail, error:%s", err)
		return
	}
	if err := node3MongodInstall.Init(node3Runtime); err != nil {
		fmt.Println(fmt.Sprintf("replicate install node3 init fail, error:%s", err))
		t.Errorf("replicate install node3 init fail, error:%s", err)
		return
	}
	if err := node3MongodInstall.Run(); err != nil {
		fmt.Println(fmt.Sprintf("replicate install node3 run fail, error:%s", err))
		t.Errorf("replicate install node3 run fail, error:%s", err)
		return
	}

	if err := node4MongodInstall.Init(node4Runtime); err != nil {
		fmt.Println(fmt.Sprintf("replicate install node3 init fail, error:%s", err))
		t.Errorf("replicate install node3 init fail, error:%s", err)
		return
	}
	if err := node4MongodInstall.Run(); err != nil {
		fmt.Println(fmt.Sprintf("replicate install node3 run fail, error:%s", err))
		t.Errorf("replicate install node3 run fail, error:%s", err)
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
		fmt.Println(fmt.Sprintf("replicate install initReplicaset init fail, error:%s", err))
		t.Errorf("replicate install initReplicaset init fail, error:%s", err)
		return
	}
	if err := initReplicaset.Run(); err != nil {
		fmt.Println(fmt.Sprintf("replicate install initReplicaset run fail, error:%s", err))
		t.Errorf("replicate install initReplicaset run fail, error:%s", err)
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
		fmt.Println(fmt.Sprintf("replicate install addAdminUser init fail, error:%s", err))
		t.Errorf("replicate install addAdminUser init fail, error:%s", err)
		return
	}
	if err := addAdminUser.Run(); err != nil {
		fmt.Println(fmt.Sprintf("replicate install addAdminUser run fail, error:%s", err))
		t.Errorf("replicate install addAdminUser run fail, error:%s", err)
		return
	}

	// 创建业务用户
	addUserParam := "{\n  \"ip\":\"{{ip}}\",\n  \"port\":27001,\n  \"instanceType\":\"mongod\",\n  \"username\":\"test\",\n  \"password\":\"test\",\n  \"adminUsername\":\"dba\",\n  \"adminPassword\":\"dba\",\n  \"authDb\":\"admin\",\n  \"dbs\":[\n\n  ],\n  \"privileges\":[\n    \"readWriteAnyDatabase\"\n  ]\n}"
	addUserParam = strings.Replace(addUserParam, "{{ip}}", ip, -1)
	addUserRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: addUserParam,
	}
	addUserRuntime.SetLogger()
	addUser := NewAddUser()
	if err := addUser.Init(addUserRuntime); err != nil {
		fmt.Println(fmt.Sprintf("replicate install addUser init fail, error:%s", err))
		t.Errorf("replicate install addUser init fail, error:%s", err)
		return
	}
	if err := addUser.Run(); err != nil {
		fmt.Println(fmt.Sprintf("replicate install addUser run fail, error:%s", err))
		t.Errorf("replicate install addUser run fail, error:%s", err)
		return
	}

	// 删除业务用户
	delUserParam := "{\n  \"ip\":\"{{ip}}\",\n  \"port\":27001,\n  \"instanceType\":\"mongod\",\n  \"adminUsername\":\"dba\",\n  \"adminPassword\":\"dba\",\n  \"username\":\"test\",\n  \"authDb\":\"admin\"\n}"
	delUserParam = strings.Replace(delUserParam, "{{ip}}", ip, -1)
	delUserRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: delUserParam,
	}
	delUserRuntime.SetLogger()
	delUser := NewDelUser()
	if err := delUser.Init(delUserRuntime); err != nil {
		fmt.Println(fmt.Sprintf("replicate install delUser init fail, error:%s", err))
		t.Errorf("replicate install delUser init fail, error:%s", err)
		return
	}
	if err := delUser.Run(); err != nil {
		fmt.Println(fmt.Sprintf("replicate install delUser run fail, error:%s", err))
		t.Errorf("replicate install delUser run fail, error:%s", err)
		return
	}

	// 执行脚本
	execScriptParam := "{\n  \"ip\":\"{{ip}}\",\n  \"port\":27001,\n  \"script\":\"var mongo = db;\\nmongo.getSisterDB('admin').runCommand({listDatabases:1}).databases.forEach (function (x) { print(x.name)});\\n\",\n  \"type\":\"replicaset\",\n  \"secondary\": false,\n  \"adminUsername\":\"dba\",\n  \"adminPassword\":\"dba\",\n  \"repoUrl\":\"\",\n  \"repoUsername\":\"\",\n  \"repoToken\":\"\",\n  \"repoProject\":\"\",\n  \"repoRepo\":\"\",\n  \"repoPath\":\"\"\n}"
	execScriptParam = strings.Replace(execScriptParam, "{{ip}}", ip, -1)
	execScriptRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: execScriptParam,
	}
	execScriptRuntime.SetLogger()
	execScript := NewExecScript()
	if err := execScript.Init(execScriptRuntime); err != nil {
		fmt.Println(fmt.Sprintf("replicate install execScript init fail, error:%s", err))
		t.Errorf("replicate install execScript init fail, error:%s", err)
		return
	}
	if err := execScript.Run(); err != nil {
		fmt.Println(fmt.Sprintf("replicate install execScript run fail, error:%s", err))
		t.Errorf("replicate install execScript run fail, error:%s", err)
		return
	}

	// 重启节点
	restartParam := "{\n  \"ip\":\"{{ip}}\",\n  \"port\":27002,\n  \"instanceType\":\"mongod\",\n  \"singleNodeInstallRestart\":false,  \n  \"auth\":true,\n  \"cacheSizeGB\": 2,\n  \"mongoSConfDbOld\":\"\",\n  \"MongoSConfDbNew\":\"\",\n  \"adminUsername\":\"dba\",\n  \"adminPassword\":\"dba\"\n}"
	restartParam = strings.Replace(restartParam, "{{ip}}", ip, -1)
	restartRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: restartParam,
	}
	restartRuntime.SetLogger()
	restart := NewMongoRestart()
	if err := restart.Init(restartRuntime); err != nil {
		fmt.Println(fmt.Sprintf("replicate install restart init fail, error:%s", err))
		t.Errorf("replicate install restart init fail, error:%s", err)
		return
	}
	if err := restart.Run(); err != nil {
		fmt.Println(fmt.Sprintf("replicate install restart run fail, error:%s", err))
		t.Errorf("replicate install restart run fail, error:%s", err)
		return
	}

	time.Sleep(time.Second * 3)
	// 替换节点
	replaceParam := "{\n  \"ip\":\"{{ip}}\",\n  \"port\":27001,\n  \"sourceIP\":\"{{ip}}\",\n  \"sourcePort\":27001,\n  \"sourceDown\":false,\n  \"adminUsername\":\"dba\",\n  \"adminPassword\":\"dba\",\n  \"targetIP\":\"{{ip}}\",\n  \"targetPort\":27004,\n  \"targetPriority\":\"\",\n  \"targetHidden\":\"\"\n}"
	replaceParam = strings.Replace(replaceParam, "{{ip}}", ip, -1)
	replaceRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: replaceParam,
	}
	replaceRuntime.SetLogger()
	replace := NewMongoDReplace()
	if err := replace.Init(replaceRuntime); err != nil {
		fmt.Println(fmt.Sprintf("replicate install replace init fail, error:%s", err))
		t.Errorf("replicate install replace init fail, error:%s", err)
		return
	}
	if err := replace.Run(); err != nil {
		fmt.Println(fmt.Sprintf("replicate install replace run fail, error:%s", err))
		t.Errorf("replicate install replace run fail, error:%s", err)
		return
	}

	time.Sleep(time.Second * 3)
	// 主从切换
	stepDownParam := "{\n    \"ip\":\"{{ip}}\",\n    \"port\":27002,\n    \"adminUsername\":\"dba\",\n    \"adminPassword\":\"dba\"\n}"
	stepDownParam = strings.Replace(stepDownParam, "{{ip}}", ip, -1)
	stepDownRuntime := &jobruntime.JobGenericRuntime{
		PayloadDecoded: stepDownParam,
	}
	stepDownRuntime.SetLogger()
	stepDown := NewStepDown()
	if err := stepDown.Init(stepDownRuntime); err != nil {
		fmt.Println(fmt.Sprintf("replicate install stepDown init fail, error:%s", err))
		t.Errorf("replicate install stepDown init fail, error:%s", err)
		return
	}
	if err := stepDown.Run(); err != nil {
		fmt.Println(fmt.Sprintf("replicate install stepDown run fail, error:%s", err))
		t.Errorf("replicate install stepDown run fail, error:%s", err)
		return
	}

	time.Sleep(time.Second * 3)
	// 下架
	for _, i := range []int{27003, 27002, 27004} {
		deinstallParam := fmt.Sprintf("{\n    \"ip\":\"{{ip}}\",\n    \"port\":%d,\n    \"app\":\"test\",\n    \"areaId\":\"test1\",\n    \"nodeInfo\":[\n        \"{{ip}}\"\n    ],\n    \"instanceType\":\"mongod\"\n}", i)
		deinstallParam = strings.Replace(deinstallParam, "{{ip}}", ip, -1)
		deinstallRuntime := &jobruntime.JobGenericRuntime{
			PayloadDecoded: deinstallParam,
		}
		deinstallRuntime.SetLogger()
		deinstal := NewDeInstall()
		if err := deinstal.Init(deinstallRuntime); err != nil {
			fmt.Println(fmt.Sprintf("replicate install deinstal port:%d init fail, error:%s", i, err))
			t.Errorf("replicate install deinstal port:%d init fail, error:%s", i, err)
			return
		}
		if err := deinstal.Run(); err != nil {
			fmt.Println(fmt.Sprintf("replicate install deinstal port:%d run fail, error:%s", i, err))
			t.Errorf("replicate install deinstal port:%d run fail, error:%s", i, err)
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
