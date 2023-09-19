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

	util "dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app"
	"dbm-services/mysql/db-simulation/app/config"

	"github.com/pkg/errors"
	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/kubernetes/scheme"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/remotecommand"
)

// Kcs TODO
var Kcs KubeClientSets

// DefaultUser TODO
const DefaultUser = "root"

// KubeClientSets TODO
type KubeClientSets struct {
	Cli        *kubernetes.Clientset
	RestConfig *rest.Config
	Namespace  string // namespace
}

// MySQLPodBaseInfo TODO
type MySQLPodBaseInfo struct {
	PodName string
	Lables  map[string]string
	RootPwd string
	Charset string
}

// DbPodSets TODO
type DbPodSets struct {
	K8S         KubeClientSets
	BaseInfo    *MySQLPodBaseInfo
	DbWork      *util.DbWorker
	DbImage     string
	TdbCtlImage string
	SpiderImage string
}

// ClusterPodSets TODO
type ClusterPodSets struct {
	DbPodSets
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
		logger.Fatal("init kubernets client failed %s", err.Error())
		return
	}
	Kcs.Cli = clientSet
	Kcs.Namespace = config.GAppConfig.Bcs.NameSpace
}

// NewDbPodSets TODO
func NewDbPodSets() *DbPodSets {
	return &DbPodSets{
		K8S: Kcs,
	}
}

func (k *DbPodSets) getCreateClusterSqls() []string {
	var ss []string
	ss = append(ss, fmt.Sprintf(
		"tdbctl create node wrapper 'SPIDER' options(user 'root', password '%s', host 'localhost', port 25000);",
		k.BaseInfo.RootPwd))
	ss = append(ss, fmt.Sprintf(
		"tdbctl create node wrapper 'mysql' options(user 'root', password '%s', host 'localhost', port 20000);",
		k.BaseInfo.RootPwd))
	ss = append(ss, fmt.Sprintf(
		"tdbctl create node wrapper 'TDBCTL' options(user 'root', password '%s', host 'localhost', port 26000);",
		k.BaseInfo.RootPwd))
	ss = append(ss, "tdbctl enable primary;")
	ss = append(ss, "tdbctl flush routing;")
	return ss
}

// CreateClusterPod TODO
func (k *DbPodSets) CreateClusterPod() (err error) {
	c := &v1.Pod{
		TypeMeta: metav1.TypeMeta{
			Kind:       "Pod",
			APIVersion: "v1",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      k.BaseInfo.PodName,
			Namespace: k.K8S.Namespace,
			Labels:    k.BaseInfo.Lables,
		},
		Spec: v1.PodSpec{
			Containers: []v1.Container{
				{
					Name: "backend",
					Env: []v1.EnvVar{{
						Name:  "MYSQL_ROOT_PASSWORD",
						Value: k.BaseInfo.RootPwd,
					}},
					ImagePullPolicy: v1.PullIfNotPresent,
					Image:           k.DbImage,
					Args: []string{"mysqld", "--defaults-file=/etc/my.cnf", "--port=20000", fmt.Sprintf("--character-set-server=%s",
						k.BaseInfo.Charset),
						"--user=mysql"},
					ReadinessProbe: &v1.Probe{
						ProbeHandler: v1.ProbeHandler{
							Exec: &v1.ExecAction{
								Command: []string{"/bin/bash", "-c", fmt.Sprintf("mysql -uroot -p%s -e 'select 1'", k.BaseInfo.RootPwd)},
							},
						},
						InitialDelaySeconds: 3,
						PeriodSeconds:       5,
					},
				}, {
					Name: "spider",
					Env: []v1.EnvVar{{
						Name:  "MYSQL_ROOT_PASSWORD",
						Value: k.BaseInfo.RootPwd,
					}},
					ImagePullPolicy: v1.PullIfNotPresent,
					Image:           k.SpiderImage,
					Args: []string{"mysqld", "--defaults-file=/etc/my.cnf", "--port=25000", fmt.Sprintf("--character-set-server=%s",
						k.BaseInfo.Charset),
						"--user=mysql"},
					ReadinessProbe: &v1.Probe{
						ProbeHandler: v1.ProbeHandler{
							Exec: &v1.ExecAction{
								Command: []string{"/bin/bash", "-c", fmt.Sprintf("mysql -uroot -p%s -e 'select 1'", k.BaseInfo.RootPwd)},
							},
						},
						InitialDelaySeconds: 3,
						PeriodSeconds:       5,
					},
				},
				{
					Name: "tdbctl",
					Env: []v1.EnvVar{{
						Name:  "MYSQL_ROOT_PASSWORD",
						Value: k.BaseInfo.RootPwd,
					}},
					ImagePullPolicy: v1.PullIfNotPresent,
					Image:           k.TdbCtlImage,
					Args: []string{"mysqld", "--defaults-file=/etc/my.cnf", "--port=26000", "--tc-admin=1",
						"--dbm-allow-standalone-primary",
						fmt.Sprintf("--character-set-server=%s",
							k.BaseInfo.Charset),
						"--user=mysql"},
					ReadinessProbe: &v1.Probe{
						ProbeHandler: v1.ProbeHandler{
							Exec: &v1.ExecAction{
								Command: []string{"/bin/bash", "-c", fmt.Sprintf("mysql -uroot -p%s -e 'select 1'", k.BaseInfo.RootPwd)},
							},
						},
						InitialDelaySeconds: 3,
						PeriodSeconds:       5,
					},
				},
			},
		},
	}
	if err := k.createpod(c, 26000); err != nil {
		logger.Error("create spider cluster failed %s", err.Error())
		return err
	}
	logger.Info("connect tdbctl success ~")
	// create cluster relation
	for _, ql := range k.getCreateClusterSqls() {
		logger.Info("exec init cluster sql %s", ql)
		if _, err = k.DbWork.Db.Exec(ql); err != nil {
			return err
		}
	}
	return nil
}

// createpod TODO
func (k *DbPodSets) createpod(pod *v1.Pod, probePort int) (err error) {
	if _, err = k.K8S.Cli.CoreV1().Pods(k.K8S.Namespace).Create(context.TODO(), pod, metav1.CreateOptions{}); err != nil {
		logger.Error("create pod failed %s", err.Error())
		return err
	}
	var podIp string
	// 连续多次探测pod的状态
	if err := util.Retry(util.RetryConfig{Times: 120, DelayTime: 2 * time.Second}, func() error {
		podI, err := k.K8S.Cli.CoreV1().Pods(k.K8S.Namespace).Get(context.TODO(), k.BaseInfo.PodName, metav1.GetOptions{})
		if err != nil {
			return err
		}
		for _, cStatus := range podI.Status.ContainerStatuses {
			logger.Info("%s: %v", cStatus.Name, cStatus.Ready)
			if !cStatus.Ready {
				return fmt.Errorf("container %s is not ready", cStatus.Name)
			}
		}
		podIp = podI.Status.PodIP
		return nil
	}); err != nil {
		return err
	}
	fn := func() error {
		k.DbWork, err = util.NewDbWorker(fmt.Sprintf("%s:%s@tcp(%s:%d)/?timeout=5s&multiStatements=true",
			DefaultUser,
			k.BaseInfo.RootPwd,
			podIp, probePort))
		if err != nil {
			logger.Error("connect to pod %s failed %s", podIp, err.Error())
			return errors.Wrap(err, "create pod success,connect to mysql pod failed")
		}
		return nil
	}
	return util.Retry(util.RetryConfig{Times: 60, DelayTime: 2 * time.Second}, fn)
}

// CreateMySQLPod TODO
func (k *DbPodSets) CreateMySQLPod() (err error) {
	c := &v1.Pod{
		TypeMeta: metav1.TypeMeta{
			Kind:       "Pod",
			APIVersion: "v1",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      k.BaseInfo.PodName,
			Namespace: k.K8S.Namespace,
			Labels:    k.BaseInfo.Lables,
		},
		Spec: v1.PodSpec{
			Containers: []v1.Container{{
				Name: app.MySQL,
				Env: []v1.EnvVar{{
					Name:  "MYSQL_ROOT_PASSWORD",
					Value: k.BaseInfo.RootPwd,
				}},
				Ports: []v1.ContainerPort{
					{ContainerPort: 3306},
				},
				ImagePullPolicy: v1.PullIfNotPresent,
				Image:           k.DbImage,
				Args: []string{"mysqld", "--defaults-file=/etc/my.cnf", fmt.Sprintf("--character-set-server=%s",
					k.BaseInfo.Charset),
					"--user=mysql"},
				ReadinessProbe: &v1.Probe{
					ProbeHandler: v1.ProbeHandler{
						Exec: &v1.ExecAction{
							Command: []string{"/bin/bash", "-c", fmt.Sprintf("mysql -uroot -p%s -e 'select 1'", k.BaseInfo.RootPwd)},
						},
					},
					InitialDelaySeconds: 2,
					PeriodSeconds:       5,
				},
			}},
		},
	}

	return k.createpod(c, 3306)
}

// DeletePod delete pod
func (k *DbPodSets) DeletePod() (err error) {
	return k.K8S.Cli.CoreV1().Pods(k.K8S.Namespace).Delete(context.TODO(), k.BaseInfo.PodName, metav1.DeleteOptions{})
}

// getLoadSchemaSQLCmd create load schema sql cmd
func (k *DbPodSets) getLoadSchemaSQLCmd(bkpath, file string) (cmd string) {
	commands := []string{}
	commands = append(commands, fmt.Sprintf("wget %s", getdownloadUrl(bkpath, file)))
	// sed -i '/50720 SET tc_admin=0/d'
	// 从中控dump的schema文件,默认是添加了tc_admin=0,需要删除
	// 因为模拟执行是需要将中控进行sql转发
	commands = append(commands, fmt.Sprintf("sed -i '/50720 SET tc_admin=0/d' %s", file))
	// sed 's/CREATE definer=.*@.* PROCEDURE/CREATE definer=`root`@`localhost` PROCEDURE/gI'
	// 需要处理存储过程、函数的definer，因为拉起的pod是root用户，所以需要将definer修改为root
	commands = append(commands, fmt.Sprintf(
		"sed -i 's/CREATE definer=.*@.* $/CREATE definer=`root`@`localhost` /gI' %s", file))
	commands = append(commands, fmt.Sprintf("mysql -uroot -p%s --default-character-set=%s -vvv < %s", k.BaseInfo.RootPwd,
		k.BaseInfo.Charset, file))
	return strings.Join(commands, " && ")
}

// getLoadSQLCmd get load sql cmd
func (k *DbPodSets) getLoadSQLCmd(bkpath, file string, dbs []string) (cmd []string) {
	// cmd = fmt.Sprintf(
	// 	"wget %s && mysql --defaults-file=/etc/my.cnf -uroot -p%s --default-character-set=%s %s < %s",
	cmd = append(cmd, fmt.Sprintf("curl -o %s %s", file, getdownloadUrl(bkpath, file)))
	for _, db := range dbs {
		cmd = append(cmd, fmt.Sprintf("mysql --defaults-file=/etc/my.cnf -uroot -p%s --default-character-set=%s -vvv %s < %s",
			k.BaseInfo.RootPwd, k.BaseInfo.Charset, db, file))
	}
	return cmd
}

func getdownloadUrl(bkpath, file string) string {
	endpoint := config.GAppConfig.BkRepo.EndPointUrl
	project := config.GAppConfig.BkRepo.Project
	publicbucket := config.GAppConfig.BkRepo.PublicBucket
	u, err := url.Parse(endpoint)
	if err != nil {
		return ""
	}
	r, err := url.Parse(path.Join("/generic", project, publicbucket, bkpath, file))
	if err != nil {
		logger.Error(err.Error())
		return ""
	}
	ll := u.ResolveReference(r).String()
	logger.Info("dbeug url is %s", ll)
	return ll
}

// executeInPod TODO
func (k *DbPodSets) executeInPod(cmd, container string, extMap map[string]string) (stdout, stderr bytes.Buffer,
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
		logger.Error("remotecommand.NewSPDYExecutor", err.Error())
		return bytes.Buffer{}, bytes.Buffer{}, err
	}
	go func() {
		buf := []byte{}
		sc := bufio.NewScanner(reader)
		sc.Buffer(buf, 2048*1024)
		lineNumber := 1
		for sc.Scan() {
			xlogger.Info(sc.Text())
			lineNumber++
		}
		if err := sc.Err(); err != nil {
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
	xlogger.Info("exec successfuly...")
	logger.Info("info stdout:%s\nstderr:%s ", strings.TrimSpace(stdout.String()),
		strings.TrimSpace(stderr.String()))
	return stdout, stderr, nil
}
