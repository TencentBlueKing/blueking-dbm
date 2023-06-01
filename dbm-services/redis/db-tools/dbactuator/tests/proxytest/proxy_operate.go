package proxytest

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomproxy"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// TwemproxyOperateTest  启停测试
type TwemproxyOperateTest struct {
	atomproxy.TwemproxyOperateParams
	Err error `json:"-"`
}

// SetIP set ip,传入为空则自动获取本地ip
func (test *TwemproxyOperateTest) SetIP(ip string) *TwemproxyOperateTest {
	if test.Err != nil {
		return test
	}
	if ip == "" || ip == "127.0.0.1" {
		ip, test.Err = util.GetLocalIP()
		if test.Err != nil {
			return test
		}
	}
	test.IP = ip
	return test
}

// SetPort set port
func (test *TwemproxyOperateTest) SetPort(port int) *TwemproxyOperateTest {
	if test.Err != nil {
		return test
	}
	test.Port = port
	return test
}

// SetOp set op
func (test *TwemproxyOperateTest) SetOp(op string) *TwemproxyOperateTest {
	if test.Err != nil {
		return test
	}
	test.Operate = op
	return test
}

// SetTest set test
func (test *TwemproxyOperateTest) SetTest() *TwemproxyOperateTest {
	if test.Err != nil {
		return test
	}
	test.Debug = true
	return test
}

// RunTwemproxyOpenClose twemproxy启停
func (test *TwemproxyOperateTest) RunTwemproxyOpenClose() {
	msg := fmt.Sprintf("=========RunTwemproxyOpenClose %s test start============", test.Operate)
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========RunTwemproxyOpenClose %s test fail============", test.Operate)
		} else {
			msg = fmt.Sprintf("=========RunTwemproxyOpenClose %s test success============", test.Operate)
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test)
	cmd := fmt.Sprintf(consts.ActuatorTestCmd, atomproxy.NewTwemproxyOperate().Name(), string(paramBytes))
	fmt.Println(cmd)
	_, test.Err = util.RunBashCmd(cmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return
	}
	return
}

// PredixyOperateTest  启停测试
type PredixyOperateTest struct {
	atomproxy.PredixyOperateParams
	Err error `json:"-"`
}

// SetIP set ip,传入为空则自动获取本地ip
func (test *PredixyOperateTest) SetIP(ip string) *PredixyOperateTest {
	if test.Err != nil {
		return test
	}
	if ip == "" || ip == "127.0.0.1" {
		ip, test.Err = util.GetLocalIP()
		if test.Err != nil {
			return test
		}
	}
	test.IP = ip
	return test
}

// SetPort set port
func (test *PredixyOperateTest) SetPort(port int) *PredixyOperateTest {
	if test.Err != nil {
		return test
	}
	test.Port = port
	return test
}

// SetOp set op
func (test *PredixyOperateTest) SetOp(op string) *PredixyOperateTest {
	if test.Err != nil {
		return test
	}
	test.Operate = op
	return test
}

// SetTest set test
func (test *PredixyOperateTest) SetTest() *PredixyOperateTest {
	if test.Err != nil {
		return test
	}
	test.Debug = true
	return test
}

// RunPredixyOpenClose Predixy启停
func (test *PredixyOperateTest) RunPredixyOpenClose() {
	msg := fmt.Sprintf("=========RunPredixyOpenClose %s test start============", test.Operate)
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========RunPredixyOpenClose %s test fail============", test.Operate)
		} else {
			msg = fmt.Sprintf("=========RunPredixyOpenClose %s test success============", test.Operate)
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test)
	cmd := fmt.Sprintf(consts.ActuatorTestCmd, atomproxy.NewPredixyOperate().Name(), string(paramBytes))
	fmt.Println(cmd)
	_, test.Err = util.RunBashCmd(cmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return
	}
	return
}

// PredixyOpenClose predixy操作测试
func PredixyOpenClose(serverIP string) (err error) {
	predixyOpenCloseTest := PredixyOperateTest{}
	predixyOpenCloseTest.SetIP(serverIP).SetPort(consts.TestPredixyPort).SetOp(consts.ProxyStop)
	if predixyOpenCloseTest.Err != nil {
		return
	}
	predixyOpenCloseTest.RunPredixyOpenClose()
	if predixyOpenCloseTest.Err != nil {
		return
	}
	predixyOpenCloseTest.SetIP(serverIP).SetPort(consts.TestPredixyPort).SetOp(consts.ProxyStart)
	if predixyOpenCloseTest.Err != nil {
		return
	}
	predixyOpenCloseTest.RunPredixyOpenClose()
	if predixyOpenCloseTest.Err != nil {
		return
	}
	return nil
}

// PredixyShutdown predixy关闭测试
func PredixyShutdown(serverIP string) (err error) {
	predixyOpenCloseTest := PredixyOperateTest{}
	predixyOpenCloseTest.SetIP(serverIP).SetPort(consts.TestPredixyPort).SetOp(consts.ProxyShutdown).SetTest()
	if predixyOpenCloseTest.Err != nil {
		return
	}
	predixyOpenCloseTest.RunPredixyOpenClose()
	if predixyOpenCloseTest.Err != nil {
		return
	}
	return nil
}

// TwemproxyOpenClose twemproxy操作测试
func TwemproxyOpenClose(serverIP string) (err error) {
	twempOpenCloseTest := TwemproxyOperateTest{}
	twempOpenCloseTest.SetIP(serverIP).SetPort(consts.TestTwemproxyPort).SetOp(consts.ProxyStop)
	if twempOpenCloseTest.Err != nil {
		return
	}
	twempOpenCloseTest.RunTwemproxyOpenClose()
	if twempOpenCloseTest.Err != nil {
		return
	}
	twempOpenCloseTest.SetIP(serverIP).SetPort(consts.TestTwemproxyPort).SetOp(consts.ProxyStart)
	if twempOpenCloseTest.Err != nil {
		return
	}
	twempOpenCloseTest.RunTwemproxyOpenClose()
	if twempOpenCloseTest.Err != nil {
		return
	}
	return nil
}

// TwemproxyShutDown twemproxy关闭测试
func TwemproxyShutDown(localIP string) (err error) {
	twempOpenCloseTest := TwemproxyOperateTest{}
	twempOpenCloseTest.SetIP(localIP).SetPort(consts.TestTwemproxyPort).SetOp(consts.ProxyShutdown).SetTest()
	if twempOpenCloseTest.Err != nil {
		return
	}
	twempOpenCloseTest.RunTwemproxyOpenClose()
	if twempOpenCloseTest.Err != nil {
		return
	}
	return nil
}
