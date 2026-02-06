/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package service

import (
	"bufio"
	"bytes"
	"context"
	"fmt"
	"io"
	"net/url"
	"os"
	"path"
	"strings"
	"time"

	"github.com/pkg/errors"
	"github.com/samber/lo"
	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/kubernetes/scheme"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/remotecommand"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app"
	"dbm-services/mysql/db-simulation/app/config"
	"dbm-services/mysql/db-simulation/model"
)

// Kcs k8s client sets
var Kcs KubeClientSets

// DefaultUser default user
const DefaultUser = "root"

// FatalError 致命错误，表示不应该继续重试的错误
type FatalError struct {
	ContainerName string
	Reason        string
	CheckCount    int
	Message       string
}

func (e *FatalError) Error() string {
	return fmt.Sprintf("container %s is in %s state, pod creation failed after %d checks: %s",
		e.ContainerName, e.Reason, e.CheckCount, e.Message)
}

// KubeClientSets k8s client sets
type KubeClientSets struct {
	Cli        *kubernetes.Clientset
	RestConfig *rest.Config
	Namespace  string // namespace
}

// MySQLPodBaseInfo mysql pod base info
type MySQLPodBaseInfo struct {
	PodName string
	Labels  map[string]string
	Args    []string
	RootPwd string
	Charset string
}

// DbPodSets db pod sets
type DbPodSets struct {
	K8S              KubeClientSets
	BaseInfo         *MySQLPodBaseInfo
	DbWork           *cmutil.DbWorker
	DbImage          string
	TdbCtlImage      string
	SpiderPods       []SpiderPodBaseInfo
	TdbCtlStartArgs  map[string]string
	BackendStartArgs map[string]string
}

// SpiderPodBaseInfo spider pod base info
type SpiderPodBaseInfo struct {
	SpiderImage     string
	SpiderVersion   string
	SpiderStartArgs map[string]string
}

func init() {
	logger.Info("start init bcs client ")
	Kcs.RestConfig = &rest.Config{
		Host:        config.GAppConfig.Bcs.EndpointUrl + "/clusters/" + config.GAppConfig.Bcs.ClusterId + "/",
		BearerToken: config.GAppConfig.Bcs.Token,
		ContentConfig: rest.ContentConfig{
			ContentType:  "application/json",
			GroupVersion: &v1.SchemeGroupVersion,
		},
		Timeout: 10 * time.Second,
	}
	clientSet, err := kubernetes.NewForConfig(Kcs.RestConfig)
	if err != nil {
		logger.Fatal("init kubernetes client failed %s", err.Error())
		return
	}
	Kcs.Cli = clientSet
	Kcs.Namespace = config.GAppConfig.Bcs.NameSpace
}

// NewDbPodSets new db pod sets
func NewDbPodSets() *DbPodSets {
	return &DbPodSets{
		K8S: Kcs,
	}
}

func (k *DbPodSets) getCreateClusterSqls() []string {
	var ss []string
	for idx, _ := range k.SpiderPods {
		spiderPort := 25000 + idx
		ss = append(ss, fmt.Sprintf(
			"tdbctl create node wrapper 'SPIDER' options(user 'root', password '%s', host '127.0.0.1', port %d);",
			k.BaseInfo.RootPwd, spiderPort))
	}
	ss = append(ss, fmt.Sprintf(
		"tdbctl create node wrapper 'mysql' options(user 'root', password '%s', host '127.0.0.1', port 20000);",
		k.BaseInfo.RootPwd))
	ss = append(ss, fmt.Sprintf(
		"tdbctl create node wrapper 'TDBCTL' options(user 'root', password '%s', host '127.0.0.1', port 26000);",
		k.BaseInfo.RootPwd))
	ss = append(ss, "tdbctl enable primary;")
	ss = append(ss, "tdbctl flush routing;")
	return ss
}

// getClusterPodContainerSpec create cluster pod container spec
// nolint
func (k *DbPodSets) getClusterPodContainerSpec() []v1.Container {
	// 简化启动参数，配置通过 ConfigMap 挂载的 my.cnf 提供
	backendArgs := []string{"mysqld", "--defaults-file=/etc/my.cnf", "--user=mysql"}
	tdbctlArgs := []string{"mysqld", "--defaults-file=/etc/my.cnf", "--user=mysql"}

	containers := []v1.Container{
		{
			Name: "backend",
			Env: []v1.EnvVar{{
				Name:  "MYSQL_ROOT_PASSWORD",
				Value: k.BaseInfo.RootPwd,
			}},
			Resources:       k.getResourceLimit(),
			ImagePullPolicy: v1.PullIfNotPresent,
			Image:           k.DbImage,
			Args:            backendArgs,
			VolumeMounts: []v1.VolumeMount{{
				Name:      "cluster-config",
				MountPath: "/etc/my.cnf",
				SubPath:   "backend-my.cnf",
			}},
			ReadinessProbe: &v1.Probe{
				ProbeHandler: v1.ProbeHandler{
					Exec: &v1.ExecAction{
						Command: []string{"/bin/bash", "-c",
							fmt.Sprintf("mysql -S/data1/mysqldata/mysql.sock -uroot -p%s -e 'select 1'", k.BaseInfo.RootPwd)},
					},
				},
				InitialDelaySeconds: 3,
				PeriodSeconds:       5,
			},
		},
	}

	// 为每个 Spider 版本创建独立的容器
	for idx, spiderPod := range k.SpiderPods {
		spiderArgs := []string{"mysqld", "--defaults-file=/etc/my.cnf", "--user=mysql"}
		containerName := fmt.Sprintf("spider-%d", idx)
		configSubPath := fmt.Sprintf("spider-%d-my.cnf", idx)

		spiderContainer := v1.Container{
			Name: containerName,
			Env: []v1.EnvVar{{
				Name:  "MYSQL_ROOT_PASSWORD",
				Value: k.BaseInfo.RootPwd,
			}},
			Resources:       k.getResourceLimit(),
			ImagePullPolicy: v1.PullIfNotPresent,
			Image:           spiderPod.SpiderImage,
			Args:            spiderArgs,
			VolumeMounts: []v1.VolumeMount{{
				Name:      "cluster-config",
				MountPath: "/etc/my.cnf",
				SubPath:   configSubPath,
			}},
			ReadinessProbe: &v1.Probe{
				ProbeHandler: v1.ProbeHandler{
					Exec: &v1.ExecAction{
						Command: []string{"/bin/bash", "-c",
							fmt.Sprintf("mysql -S/data1/mysqldata/mysql.sock -uroot -p%s -e 'select 1'", k.BaseInfo.RootPwd)},
					},
				},
				InitialDelaySeconds: 3,
				PeriodSeconds:       5,
			},
		}
		containers = append(containers, spiderContainer)
	}

	// 添加 tdbctl 容器
	tdbctlContainer := v1.Container{
		Name: "tdbctl",
		Env: []v1.EnvVar{{
			Name:  "MYSQL_ROOT_PASSWORD",
			Value: k.BaseInfo.RootPwd,
		}},
		Resources:       k.getTdbctlResourceLimit(),
		ImagePullPolicy: v1.PullIfNotPresent,
		Image:           k.TdbCtlImage,
		Args:            tdbctlArgs,
		VolumeMounts: []v1.VolumeMount{{
			Name:      "cluster-config",
			MountPath: "/etc/my.cnf",
			SubPath:   "tdbctl-my.cnf",
		}},
		ReadinessProbe: &v1.Probe{
			ProbeHandler: v1.ProbeHandler{
				Exec: &v1.ExecAction{
					Command: []string{"/bin/bash", "-c",
						fmt.Sprintf("mysql -S/data1/mysqldata/mysql.sock -uroot -p%s -e 'select 1'", k.BaseInfo.RootPwd)},
				},
			},
			InitialDelaySeconds: 3,
			PeriodSeconds:       5,
		},
	}
	containers = append(containers, tdbctlContainer)

	return containers
}

// CreateClusterPod create tendbcluster simulation pod
func (k *DbPodSets) CreateClusterPod(mySQLVersion string, xlogger *logger.Logger) (err error) {
	// 创建 ConfigMap 存储 my.cnf 配置
	if err = k.createClusterConfigMap(mySQLVersion); err != nil {
		return err
	}

	configMapName := k.getClusterConfigMapName()
	logger.Info("created cluster config map: %s", configMapName)

	c := &v1.Pod{
		TypeMeta: metav1.TypeMeta{
			Kind:       "Pod",
			APIVersion: "v1",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      k.BaseInfo.PodName,
			Namespace: k.K8S.Namespace,
			Labels:    k.BaseInfo.Labels,
		},
		Spec: v1.PodSpec{
			NodeSelector: lo.SliceToMap(config.GAppConfig.SimulationNodeLables, func(item config.LabelItem) (k, v string) {
				return item.Key,
					item.Value
			}),
			Tolerations: k.getToleration(),
			// 定义 ConfigMap Volume
			Volumes: []v1.Volume{{
				Name: "cluster-config",
				VolumeSource: v1.VolumeSource{
					ConfigMap: &v1.ConfigMapVolumeSource{
						LocalObjectReference: v1.LocalObjectReference{
							Name: configMapName,
						},
					},
				},
			}},
			Containers: k.getClusterPodContainerSpec(),
		},
	}
	if err = k.createPod(c, 26000, xlogger); err != nil {
		logger.Error("create spider cluster failed %s", err.Error())
		if deleteErr := k.deleteClusterConfigMap(); deleteErr != nil {
			logger.Error("delete cluster configMap failed %s", deleteErr.Error())
		}
		return err
	}
	logger.Info("connect tdbctl success ~")
	// create cluster relation
	for _, sql := range k.getCreateClusterSqls() {
		if _, err = k.DbWork.Db.Exec(sql); err != nil {
			return err
		}
	}
	return nil
}

// CreatePod create pod
func (k *DbPodSets) createPod(pod *v1.Pod, probePort int, xlogger *logger.Logger) (err error) {
	if xlogger == nil {
		xlogger = logger.New(os.Stdout, true, logger.InfoLevel, map[string]string{"pod_name": k.BaseInfo.PodName})
	}
	podc, err := k.K8S.Cli.CoreV1().Pods(k.K8S.Namespace).Create(context.TODO(), pod, metav1.CreateOptions{})
	if err != nil {
		logger.Error("create pod failed %s", err.Error())
		return err
	}
	uid := string(podc.GetUID())
	model.DB.Create(&model.TbContainerRecord{
		Container:     k.BaseInfo.PodName,
		Uid:           uid,
		CreatePodTime: time.Now(),
		CreateTime:    time.Now()})
	podIp := podc.Status.PodIP
	// 用于跟踪每个容器的 CrashLoopBackOff 连续出现次数（按容器名称分别跟踪）
	crashLoopCounts := make(map[string]int)
	const maxCrashLoopChecks = 3 // 连续 3 次检测到 CrashLoopBackOff 就退出
	// 自定义重试循环，支持提前退出
	maxRetries := 120
	retryDelay := 2 * time.Second
	var lastErr error
	// 连续多次探测pod的状态
	fn := func() (err error) {
		var podI *v1.Pod
		podI, err = k.K8S.Cli.CoreV1().Pods(k.K8S.Namespace).Get(context.TODO(), k.BaseInfo.PodName, metav1.GetOptions{})
		if err != nil {
			return err
		}
		if len(podI.Status.ContainerStatuses) == 0 {
			return fmt.Errorf("get pod status is empty,wait some seconds")
		}
		for _, cStatus := range podI.Status.ContainerStatuses {
			logger.Info("%s: %v, RestartCount: %d", cStatus.Name, cStatus.Ready, cStatus.RestartCount)

			// 检测容器不 Ready 的情况
			if !cStatus.Ready {
				// 检查容器是否处于 crash 状态 - 先检查这个，因为需要尽早退出
				if cStatus.State.Waiting != nil {
					reason := cStatus.State.Waiting.Reason
					if reason == "CrashLoopBackOff" || reason == "Error" {
						// 增加该容器的 crash 计数
						crashLoopCounts[cStatus.Name]++
						currentCount := crashLoopCounts[cStatus.Name]

						xlogger.Error("container %s is in %s state: %s (detected %d times)",
							cStatus.Name, reason, cStatus.State.Waiting.Message, currentCount)

						// 输出 Pod 中所有容器的镜像信息
						containersInfo := k.getPodContainersInfo(podI)
						xlogger.Error("%s", containersInfo)

						// 抓取日志（使用 xlogger 输出到前端）
						logs, logErr := k.getContainerLogs(k.BaseInfo.PodName, cStatus.Name, 100)
						if logErr != nil {
							xlogger.Error("failed to get crash logs: %s", logErr.Error())
						} else {
							xlogger.Error("========== Container %s Crash Logs ==========", cStatus.Name)
							xlogger.Error("%s", logs)
							xlogger.Error("========== End of Crash Logs ==========")
						}

						// 连续多次检测到 CrashLoopBackOff，停止重试
						if currentCount >= maxCrashLoopChecks {
							xlogger.Error("container %s has been in %s state for %d consecutive checks, stopping retry...",
								cStatus.Name, reason, currentCount)
							// 返回致命错误，外层会检测并立即退出重试循环
							return &FatalError{
								ContainerName: cStatus.Name,
								Reason:        reason,
								CheckCount:    currentCount,
								Message:       cStatus.State.Waiting.Message,
							}
						}
					} else {
						// 如果容器状态不是 CrashLoopBackOff，重置该容器的计数器
						crashLoopCounts[cStatus.Name] = 0
					}
				}

				// 检测容器 crash 状态 - 重启次数检查
				if cStatus.RestartCount > 2 {
					// 容器反复重启，抓取日志（使用 xlogger 输出到前端）
					xlogger.Warn("container %s has restarted %d times (not ready), fetching logs...",
						cStatus.Name, cStatus.RestartCount)

					// 输出 Pod 中所有容器的镜像信息
					containersInfo := k.getPodContainersInfo(podI)
					xlogger.Error("%s", containersInfo)

					logs, logErr := k.getContainerLogs(k.BaseInfo.PodName, cStatus.Name, 200)
					if logErr != nil {
						xlogger.Error("failed to get logs for container %s: %s", cStatus.Name, logErr.Error())
					} else {
						xlogger.Error("========== Container %s Crash Logs (last 200 lines) ==========", cStatus.Name)
						xlogger.Error("%s", logs)
						xlogger.Error("========== End of Container %s Logs ==========", cStatus.Name)
					}
				}

				return fmt.Errorf("container %s is not ready", cStatus.Name)
			}
			for _, podCondition := range podI.Status.Conditions {
				if podI.Status.Phase != v1.PodRunning {
					logger.Warn("%s: %v", podCondition.Status, podCondition.Message, podCondition.Reason)
				}
			}
		}
		podIp = podI.Status.PodIP
		logger.Info("the pod is ready,ip is %s", podIp)
		return nil
	}

	// 自定义重试循环，支持检测到致命错误时立即退出
	for i := 0; i < maxRetries; i++ {
		lastErr = fn()
		if lastErr == nil {
			// 成功，退出循环
			break
		}

		// 检查是否为致命错误（CrashLoopBackOff）
		var fatalErr *FatalError
		if errors.As(lastErr, &fatalErr) {
			xlogger.Error("detected fatal error, stopping retry immediately: %s", fatalErr.Error())
			return fatalErr
		}

		// 普通错误，继续重试
		logger.Warn("第%d次重试,函数错误:%s", i, lastErr.Error())
		if i < maxRetries-1 {
			time.Sleep(retryDelay)
		}
	}

	// 如果最终还是失败，返回错误
	if lastErr != nil {
		return errors.Wrap(lastErr, "retries exceeded")
	}
	logger.Info("the podIp is %s", podIp)
	fnc := func() error {
		k.DbWork, err = cmutil.NewDbWorker(fmt.Sprintf("%s:%s@tcp(%s:%d)/?timeout=5s&multiStatements=true",
			DefaultUser,
			k.BaseInfo.RootPwd,
			podIp, probePort))
		if err != nil {
			logger.Error("connect to pod %s failed %s", podIp, err.Error())
			return errors.Wrap(err, "create pod success,connect to mysql pod failed")
		}
		return nil
	}
	if err = cmutil.Retry(cmutil.RetryConfig{Times: 60, DelayTime: 1 * time.Second}, fnc); err == nil {
		model.UpdateTbContainerRecord(k.BaseInfo.PodName)
	}
	_, errx := k.DbWork.Db.Exec("create user ADMIN@localhost;")
	if errx != nil {
		logger.Error("create user ADMIN@localhost failed %s", errx.Error())
	}
	_, errx = k.DbWork.Db.Exec("grant all on *.* to ADMIN@localhost;")
	if errx != nil {
		logger.Error("grants user failed %s", errx.Error())
	}
	return err
}

// getContainerLogs 使用 k8s 原生接口获取容器日志
func (k *DbPodSets) getContainerLogs(podName, containerName string, tailLines int64) (string, error) {
	podLogOpts := v1.PodLogOptions{
		Container: containerName,
		TailLines: &tailLines, // 获取最后 N 行日志
	}

	req := k.K8S.Cli.CoreV1().Pods(k.K8S.Namespace).GetLogs(podName, &podLogOpts)
	podLogs, err := req.Stream(context.TODO())
	if err != nil {
		return "", err
	}
	defer podLogs.Close()

	buf := new(bytes.Buffer)
	_, err = io.Copy(buf, podLogs)
	if err != nil {
		return "", err
	}

	return buf.String(), nil
}

// getPodContainersInfo 获取 Pod 中所有容器的镜像信息
func (k *DbPodSets) getPodContainersInfo(podI *v1.Pod) string {
	var info []string
	info = append(info, "Pod Containers Information:")

	for _, container := range podI.Spec.Containers {
		// 查找对应的状态信息
		var status string
		var restartCount int32
		for _, cStatus := range podI.Status.ContainerStatuses {
			if cStatus.Name == container.Name {
				switch {
				case cStatus.Ready:
					status = "Ready"
				case cStatus.State.Waiting != nil:
					status = fmt.Sprintf("Waiting (%s)", cStatus.State.Waiting.Reason)
				case cStatus.State.Terminated != nil:
					status = fmt.Sprintf("Terminated (%s)", cStatus.State.Terminated.Reason)
				default:
					status = "Not Ready"
				}
				restartCount = cStatus.RestartCount
				break
			}
		}

		info = append(info, fmt.Sprintf("  - Container: %s", container.Name))
		info = append(info, fmt.Sprintf("    Image: %s", container.Image))
		info = append(info, fmt.Sprintf("    Status: %s", status))
		info = append(info, fmt.Sprintf("    Restart Count: %d", restartCount))
	}

	return strings.Join(info, "\n")
}

// getToleration special  node
func (k *DbPodSets) getToleration() []v1.Toleration {
	ts := []v1.Toleration{}
	for _, item := range config.GAppConfig.SimulationNodeLables {
		ts = append(ts, v1.Toleration{
			Key: item.Key,

			Operator: v1.TolerationOpExists,
		})
	}
	return ts
}

func (k *DbPodSets) getResourceLimit() v1.ResourceRequirements {
	if !config.IsEmptyMySQLPodResourceConfig() {
		return v1.ResourceRequirements{
			Limits: v1.ResourceList{
				v1.ResourceCPU:    resource.MustParse(config.GAppConfig.MySQLPodResource.Limits.Cpu),
				v1.ResourceMemory: resource.MustParse(config.GAppConfig.MySQLPodResource.Limits.Mem),
			},
			Requests: v1.ResourceList{
				v1.ResourceCPU:    resource.MustParse(config.GAppConfig.MySQLPodResource.Requests.Cpu),
				v1.ResourceMemory: resource.MustParse(config.GAppConfig.MySQLPodResource.Requests.Mem),
			},
		}
	}
	return v1.ResourceRequirements{}
}

func (k *DbPodSets) getTdbctlResourceLimit() v1.ResourceRequirements {
	if !config.IsEmptyTdbctlPodResourceConfig() {
		return v1.ResourceRequirements{
			Limits: v1.ResourceList{
				v1.ResourceCPU:    resource.MustParse(config.GAppConfig.TdbctlPodResource.Limits.Cpu),
				v1.ResourceMemory: resource.MustParse(config.GAppConfig.TdbctlPodResource.Limits.Mem),
			},
			Requests: v1.ResourceList{
				v1.ResourceCPU:    resource.MustParse(config.GAppConfig.TdbctlPodResource.Requests.Cpu),
				v1.ResourceMemory: resource.MustParse(config.GAppConfig.TdbctlPodResource.Requests.Mem),
			},
		}
	}
	return v1.ResourceRequirements{}
}

// getConfigMapName returns the ConfigMap name for the pod
func (k *DbPodSets) getConfigMapName() string {
	return fmt.Sprintf("%s-mycnf", k.BaseInfo.PodName)
}

// generateMyCnfContent generates my.cnf content from MySQL start arguments
func (k *DbPodSets) generateMyCnfContent(mysqlVersion string) string {
	var lines []string

	// [client] section
	lines = append(lines, "[client]")
	lines = append(lines, "socket=/data1/mysqldata/mysql.sock")
	lines = append(lines, "")

	// [mysqld] section
	lines = append(lines, "[mysqld]")
	// 数据目录和日志配置
	lines = append(lines, "datadir=/data1/mysqldata/data")
	lines = append(lines, "innodb_data_home_dir=/data1/mysqldata/innodb/data")
	lines = append(lines, "innodb_log_group_home_dir=/data1/mysqldata/innodb/log")
	lines = append(lines, "log_bin=/data1/mysqldata/binlog/binlog.bin")
	lines = append(lines, "relay_log=/data1/mysqldata/relay-log/relay-log.bin")
	lines = append(lines, "log_error=/data1/mysqldata/data/server_error.log")
	lines = append(lines, "tmpdir=/data1/mysqldata/tmp")
	lines = append(lines, "socket=/data1/mysqldata/mysql.sock")
	lines = append(lines, "server_id=123")

	// 基础配置
	lines = append(lines, "port=3306")
	lines = append(lines, "skip-log-bin")
	lines = append(lines, "max_allowed_packet=1073741824")
	lines = append(lines, fmt.Sprintf("character-set-server=%s", k.BaseInfo.Charset))

	// MySQL 8.0+ 专用配置
	if cmutil.MySQLVersionParse(mysqlVersion) >= cmutil.MySQLVersionParse("8.0.0") {
		lines = append(lines, "default-authentication-plugin=mysql_native_password")
	}

	for key, val := range k.BackendStartArgs {
		if lo.IsEmpty(key) {
			continue
		}
		if strings.TrimSpace(key) == "lower_case_table_names" && strings.TrimSpace(val) == "0" {
			continue
		}
		lines = append(lines, fmt.Sprintf("%s=%s", key, val))
	}

	// [mysqld-5.7] section - MySQL 5.7 专用配置
	lines = append(lines, "")
	lines = append(lines, "[mysqld-5.7]")
	lines = append(lines, "log_timestamps=1")

	return strings.Join(lines, "\n")
}

// createMySQLConfigMap creates a ConfigMap containing my.cnf for the MySQL pod
func (k *DbPodSets) createMySQLConfigMap(mysqlVersion string) error {
	configMapName := k.getConfigMapName()
	myCnfContent := k.generateMyCnfContent(mysqlVersion)

	configMap := &v1.ConfigMap{
		TypeMeta: metav1.TypeMeta{
			Kind:       "ConfigMap",
			APIVersion: "v1",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      configMapName,
			Namespace: k.K8S.Namespace,
			Labels:    k.BaseInfo.Labels,
		},
		Data: map[string]string{
			"my.cnf": myCnfContent,
		},
	}

	_, err := k.K8S.Cli.CoreV1().ConfigMaps(k.K8S.Namespace).Create(context.TODO(), configMap, metav1.CreateOptions{})
	if err != nil {
		logger.Error("create config map %s failed: %s", configMapName, err.Error())
		return errors.Wrap(err, "create mysql config map failed")
	}
	logger.Info("created config map %s with my.cnf content", configMapName)
	return nil
}

// deleteConfigMap deletes the ConfigMap associated with the pod
func (k *DbPodSets) deleteConfigMap() error {
	configMapName := k.getConfigMapName()
	err := k.K8S.Cli.CoreV1().ConfigMaps(k.K8S.Namespace).Delete(context.TODO(), configMapName, metav1.DeleteOptions{})
	if err != nil {
		logger.Warn("delete config map %s failed: %s", configMapName, err.Error())
		return err
	}
	logger.Info("deleted config map %s", configMapName)
	return nil
}

// getClusterConfigMapName returns the ConfigMap name for cluster pod
func (k *DbPodSets) getClusterConfigMapName() string {
	return fmt.Sprintf("%s-cluster-mycnf", k.BaseInfo.PodName)
}

// generateBackendMyCnfContent generates my.cnf content for backend container
func (k *DbPodSets) generateBackendMyCnfContent(mysqlVersion string) string {
	var lines []string

	// [client] section
	lines = append(lines, "[client]")
	lines = append(lines, "socket=/data1/mysqldata/mysql.sock")
	lines = append(lines, "")

	// [mysqld] section
	lines = append(lines, "[mysqld]")
	lines = append(lines, "datadir=/data1/mysqldata/data")
	lines = append(lines, "innodb_data_home_dir=/data1/mysqldata/innodb/data")
	lines = append(lines, "innodb_log_group_home_dir=/data1/mysqldata/innodb/log")
	lines = append(lines, "log_bin=/data1/mysqldata/binlog/binlog.bin")
	lines = append(lines, "relay_log=/data1/mysqldata/relay-log/relay-log.bin")
	lines = append(lines, "log_error=/data1/mysqldata/data/server_error.log")
	lines = append(lines, "tmpdir=/data1/mysqldata/tmp")
	lines = append(lines, "socket=/data1/mysqldata/mysql.sock")
	lines = append(lines, "server_id=123")
	lines = append(lines, "port=20000")
	lines = append(lines, "log_bin_trust_function_creators=1")
	lines = append(lines, "sql-mode=")
	lines = append(lines, "max_allowed_packet=1073741824")
	lines = append(lines, fmt.Sprintf("character-set-server=%s", k.BaseInfo.Charset))

	if cmutil.MySQLVersionParse(mysqlVersion) >= cmutil.MySQLVersionParse("8.0.0") {
		lines = append(lines, "default-authentication-plugin=mysql_native_password")
	}

	for key, val := range k.BackendStartArgs {
		if lo.IsEmpty(key) {
			continue
		}
		if strings.TrimSpace(key) == "lower_case_table_names" && strings.TrimSpace(val) == "0" {
			continue
		}
		lines = append(lines, fmt.Sprintf("%s=%s", key, val))
	}

	// [mysqld-5.7] section
	lines = append(lines, "")
	lines = append(lines, "[mysqld-5.7]")
	lines = append(lines, "log_timestamps=1")

	return strings.Join(lines, "\n")
}

// generateSpiderMyCnfContent generates my.cnf content for spider container
// idx: Spider 容器的索引，用于分配端口和 server_id
// spiderStartArgs: 该 Spider 版本的启动参数
func (k *DbPodSets) generateSpiderMyCnfContent(idx int, spiderStartArgs map[string]string) string {
	var lines []string

	// 端口从 25000 开始递增
	port := 25000 + idx
	// server_id 从 124 开始递增
	serverId := 124 + idx

	// [client] section
	lines = append(lines, "[client]")
	lines = append(lines, "socket=/data1/mysqldata/mysql.sock")
	lines = append(lines, "")

	// [mysqld] section
	lines = append(lines, "[mysqld]")
	lines = append(lines, "datadir=/data1/mysqldata/data")
	lines = append(lines, "innodb_data_home_dir=/data1/mysqldata/innodb/data")
	lines = append(lines, "innodb_log_group_home_dir=/data1/mysqldata/innodb/log")
	lines = append(lines, "log_bin=/data1/mysqldata/binlog/binlog.bin")
	lines = append(lines, "log_error=/data1/mysqldata/data/server_error.log")
	lines = append(lines, "tmpdir=/data1/mysqldata/tmp")
	lines = append(lines, "socket=/data1/mysqldata/mysql.sock")
	lines = append(lines, fmt.Sprintf("server_id=%d", serverId))
	lines = append(lines, fmt.Sprintf("port=%d", port))
	lines = append(lines, "max_allowed_packet=1073741824")
	lines = append(lines, fmt.Sprintf("character-set-server=%s", k.BaseInfo.Charset))

	for key, val := range spiderStartArgs {
		if lo.IsEmpty(key) {
			continue
		}
		lines = append(lines, fmt.Sprintf("%s=%s", key, val))
	}
	// [mysqld-5.7] section
	lines = append(lines, "")
	lines = append(lines, "[mysqld-5.7]")
	lines = append(lines, "log_timestamps=1")

	return strings.Join(lines, "\n")
}

// generateTdbctlMyCnfContent generates my.cnf content for tdbctl container
func (k *DbPodSets) generateTdbctlMyCnfContent() string {
	var lines []string

	// [client] section
	lines = append(lines, "[client]")
	lines = append(lines, "socket=/data1/mysqldata/mysql.sock")
	lines = append(lines, "")

	// [mysqld] section
	lines = append(lines, "[mysqld]")
	lines = append(lines, "datadir=/data1/mysqldata/data")
	lines = append(lines, "innodb_data_home_dir=/data1/mysqldata/innodb/data")
	lines = append(lines, "innodb_log_group_home_dir=/data1/mysqldata/innodb/log")
	lines = append(lines, "log_bin=/data1/mysqldata/binlog/binlog.bin")
	lines = append(lines, "log_error=/data1/mysqldata/data/server_error.log")
	lines = append(lines, "tmpdir=/data1/mysqldata/tmp")
	lines = append(lines, "socket=/data1/mysqldata/mysql.sock")
	lines = append(lines, "server_id=125")
	lines = append(lines, "port=26000")
	lines = append(lines, "tc-admin=1")
	lines = append(lines, "dbm-allow-standalone-primary")
	lines = append(lines, "max_allowed_packet=1073741824")
	lines = append(lines, fmt.Sprintf("character-set-server=%s", k.BaseInfo.Charset))

	for key, val := range k.TdbCtlStartArgs {
		if lo.IsEmpty(key) {
			continue
		}
		lines = append(lines, fmt.Sprintf("%s=%s", key, val))
	}
	// [mysqld-5.7] section
	lines = append(lines, "")
	lines = append(lines, "[mysqld-5.7]")
	lines = append(lines, "log_timestamps=1")

	return strings.Join(lines, "\n")
}

// createClusterConfigMap creates a ConfigMap containing my.cnf for all cluster containers
func (k *DbPodSets) createClusterConfigMap(mysqlVersion string) error {
	configMapName := k.getClusterConfigMapName()

	// 构建 ConfigMap 数据
	configData := map[string]string{
		"backend-my.cnf": k.generateBackendMyCnfContent(mysqlVersion),
		"tdbctl-my.cnf":  k.generateTdbctlMyCnfContent(),
	}

	// 为每个 Spider 版本生成独立的配置文件
	for idx, spiderPod := range k.SpiderPods {
		configKey := fmt.Sprintf("spider-%d-my.cnf", idx)
		configData[configKey] = k.generateSpiderMyCnfContent(idx, spiderPod.SpiderStartArgs)
		logger.Info("generated spider config: %s for version: %s", configKey, spiderPod.SpiderVersion)
	}

	configMap := &v1.ConfigMap{
		TypeMeta: metav1.TypeMeta{
			Kind:       "ConfigMap",
			APIVersion: "v1",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      configMapName,
			Namespace: k.K8S.Namespace,
			Labels:    k.BaseInfo.Labels,
		},
		Data: configData,
	}

	_, err := k.K8S.Cli.CoreV1().ConfigMaps(k.K8S.Namespace).Create(context.TODO(), configMap, metav1.CreateOptions{})
	if err != nil {
		logger.Error("create cluster config map %s failed: %s", configMapName, err.Error())
		return errors.Wrap(err, "create cluster config map failed")
	}
	logger.Info("created cluster config map %s with %d spider configs", configMapName, len(k.SpiderPods))
	return nil
}

// deleteClusterConfigMap deletes the cluster ConfigMap
func (k *DbPodSets) deleteClusterConfigMap() error {
	configMapName := k.getClusterConfigMapName()
	err := k.K8S.Cli.CoreV1().ConfigMaps(k.K8S.Namespace).Delete(context.TODO(), configMapName, metav1.DeleteOptions{})
	if err != nil {
		logger.Warn("delete cluster conf igmap %s failed: %s", configMapName, err.Error())
		return err
	}
	logger.Info("deleted cluster config map %s", configMapName)
	return nil
}

// CreateMySQLPod create mysql pod
func (k *DbPodSets) CreateMySQLPod(mysqlVersion string, xlogger *logger.Logger) (err error) {
	// 创建 ConfigMap 存储 my.cnf 配置
	if err = k.createMySQLConfigMap(mysqlVersion); err != nil {
		return err
	}

	configMapName := k.getConfigMapName()
	// 简化启动参数，配置通过 ConfigMap 挂载的 my.cnf 提供
	startArgs := []string{
		"mysqld",
		"--defaults-file=/etc/my.cnf",
		"--user=mysql",
	}
	logger.Info("start pod args %v, config map: %s", startArgs, configMapName)

	c := &v1.Pod{
		TypeMeta: metav1.TypeMeta{
			Kind:       "Pod",
			APIVersion: "v1",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      k.BaseInfo.PodName,
			Namespace: k.K8S.Namespace,
			Labels:    k.BaseInfo.Labels,
		},
		Spec: v1.PodSpec{
			NodeSelector: lo.SliceToMap(config.GAppConfig.SimulationNodeLables, func(item config.LabelItem) (k, v string) {
				return item.Key,
					item.Value
			}),
			Tolerations: k.getToleration(),
			// 定义 ConfigMap Volume
			Volumes: []v1.Volume{{
				Name: "mysql-config",
				VolumeSource: v1.VolumeSource{
					ConfigMap: &v1.ConfigMapVolumeSource{
						LocalObjectReference: v1.LocalObjectReference{
							Name: configMapName,
						},
					},
				},
			}},
			Containers: []v1.Container{{
				Resources: k.getResourceLimit(),
				Name:      app.MySQL,
				Env: []v1.EnvVar{{
					Name:  "MYSQL_ROOT_PASSWORD",
					Value: k.BaseInfo.RootPwd,
				}},
				Ports: []v1.ContainerPort{
					{ContainerPort: 3306},
				},
				ImagePullPolicy: v1.PullIfNotPresent,
				Image:           k.DbImage,
				Args:            startArgs,
				// 挂载 ConfigMap 到 /etc/my.cnf
				VolumeMounts: []v1.VolumeMount{{
					Name:      "mysql-config",
					MountPath: "/etc/my.cnf",
					SubPath:   "my.cnf",
				}},
				ReadinessProbe: &v1.Probe{
					ProbeHandler: v1.ProbeHandler{
						Exec: &v1.ExecAction{
							Command: []string{"/bin/bash", "-c",
								fmt.Sprintf("mysql -S/data1/mysqldata/mysql.sock -uroot -p%s -e 'select 1'", k.BaseInfo.RootPwd)},
						},
					},
					InitialDelaySeconds: 2,
					PeriodSeconds:       5,
				},
			}},
		},
	}

	return k.createPod(c, 3306, xlogger)
}

// DeletePod delete pod and associated ConfigMap
func (k *DbPodSets) DeletePod() (err error) {
	// 删除 Pod
	err = k.K8S.Cli.CoreV1().Pods(k.K8S.Namespace).Delete(context.TODO(), k.BaseInfo.PodName, metav1.DeleteOptions{})
	if err != nil {
		logger.Error("delete pod %s failed: %s", k.BaseInfo.PodName, err.Error())
	}
	// 删除关联的 ConfigMap（忽略错误，因为 ConfigMap 可能不存在）
	_ = k.deleteConfigMap()
	// 删除 Cluster ConfigMap（忽略错误，因为可能不存在）
	_ = k.deleteClusterConfigMap()
	return err
}

// getLoadSchemaSQLCmd create load schema sql cmd
func (k *DbPodSets) getLoadSchemaSQLCmd(bkpath, file string) (cmd string) {
	commands := []string{}
	commands = append(commands, k.getDownloadSqlCmd(bkpath, file))
	// sed -i '/50720 SET tc_admin=0/d'
	// 从中控dump的schema文件,默认是添加了tc_admin=0,需要删除
	// 因为模拟执行是需要将中控进行sql转发
	commands = append(commands, fmt.Sprintf("sed -i '/50720 SET tc_admin=0/d' %s", file))
	// del definer: 兼容 DEFINER=`user`@`host`（如 CREATE DEFINER=`ADMIN`@`localhost`）与 DEFINER='user'@'host' 两种格式
	commands = append(commands, fmt.Sprintf("sed -i 's/[[:space:]]DEFINER=`[^`]*`@`[^`]*`//g' %s", file))
	commands = append(commands, fmt.Sprintf("sed -i \"s/[[:space:]]DEFINER='[^']*'@'[^']*'//g\" %s", file))
	commands = append(commands, fmt.Sprintf("mysql -uroot -p%s --default-character-set=%s -vvv < %s", k.BaseInfo.RootPwd,
		k.BaseInfo.Charset, file))
	return strings.Join(commands, " && ")
}

// getExecuteSQLCmds 获取针对单个数据库的 SQL 执行命令列表
// 包括清理 DEFINER 和执行 SQL 的命令
func (k *DbPodSets) getExecuteSQLCmds(file, db string) []string {
	return []string{
		fmt.Sprintf("sed -i 's/[[:space:]]DEFINER=`[^`]*`@`[^`]*`//g' %s", file),
		fmt.Sprintf("sed -i \"s/[[:space:]]DEFINER='[^']*'@'[^']*'//g\" %s", file),
		fmt.Sprintf("mysql --defaults-file=/etc/my.cnf -uroot -p%s --default-character-set=%s -vvv %s < %s",
			k.BaseInfo.RootPwd, k.BaseInfo.Charset, db, file),
	}
}

func (k *DbPodSets) getDownloadSqlCmd(bkpath, file string) string {
	downloadCmd := fmt.Sprintf("curl -s -S -o %s %s", file, getdownLoadUrl(bkpath, file))
	if cmutil.IsNotEmpty(config.GAppConfig.BkRepo.User) && cmutil.IsNotEmpty(config.GAppConfig.BkRepo.Pwd) {
		downloadCmd = fmt.Sprintf("curl -u %s:%s  -s -S -o %s %s", config.GAppConfig.BkRepo.User,
			config.GAppConfig.BkRepo.Pwd, file, getdownLoadUrl(bkpath, file))
	}
	return downloadCmd
}

func getdownLoadUrl(bkpath, file string) string {
	endpoint := config.GAppConfig.BkRepo.EndPointUrl
	project := config.GAppConfig.BkRepo.Project
	publicBucket := config.GAppConfig.BkRepo.PublicBucket
	u, err := url.Parse(endpoint)
	if err != nil {
		return ""
	}
	r, err := url.Parse(path.Join("/generic", project, publicBucket, bkpath, file))
	if err != nil {
		logger.Error(err.Error())
		return ""
	}
	ll := u.ResolveReference(r).String()
	logger.Info("download url: %s", ll)
	return ll
}

// executeInPod TODO
func (k *DbPodSets) executeInPod(cmd, container string, extMap map[string]string, noLogger bool) (stdout,
	stderr bytes.Buffer,
	err error) {
	xlogger := logger.New(os.Stdout, true, logger.InfoLevel, extMap)
	logger.Info("start exec...")
	req := k.K8S.Cli.CoreV1().RESTClient().Post().Resource("pods").Name(k.BaseInfo.PodName).Namespace(k.K8S.Namespace).
		SubResource("exec").
		Param("container", container)
	logger.Info(cmd)
	req.VersionedParams(
		&v1.PodExecOptions{
			Command: []string{"/bin/bash", "-c", cmd},
			Stdin:   false,
			Stdout:  true,
			Stderr:  true,
		},
		scheme.ParameterCodec,
	)
	reader, writer := io.Pipe()
	exec, err := remotecommand.NewSPDYExecutor(k.K8S.RestConfig, "POST", req.URL())
	if err != nil {
		logger.Error("at remotecommand.NewSPDYExecutor %s", err.Error())
		return bytes.Buffer{}, bytes.Buffer{}, err
	}
	// 导入表结构的时候不打印普通非关键日志

	go func() {
		buf := []byte{}
		sc := bufio.NewScanner(reader)
		sc.Buffer(buf, 2048*1024)
		lineNumber := 1
		for sc.Scan() {
			if !noLogger {
				// 此方案打印的日志会在前端展示
				xlogger.Info("%s", sc.Text())
			} else {
				logger.Info(sc.Text())
			}
			lineNumber++
		}
		if err = sc.Err(); err != nil {
			logger.Error("something bad happened in the line %v: %v", lineNumber, err)
			return
		}
	}()
	err = exec.StreamWithContext(context.Background(), remotecommand.StreamOptions{
		Stdin:  nil,
		Stdout: writer,
		Stderr: &stderr,
		Tty:    false,
	})
	if err != nil {
		xlogger.Error("exec.Stream failed %s:\n stdout:%s\n stderr: %s", err.Error(), strings.TrimSpace(stdout.String()),
			strings.TrimSpace(stderr.String()))
		return stdout, stderr, err
	}
	xlogger.Info("exec successfully...")
	logger.Info("info stdout:%s\nstderr:%s ", strings.TrimSpace(stdout.String()),
		strings.TrimSpace(stderr.String()))
	return stdout, stderr, nil
}
