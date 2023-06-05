// Package osutil TODO
/*
 * @Author: your name
 * @Date: 2022-04-21 15:07:16
 * @LastEditTime: 2022-04-21 15:07:16
 * @LastEditors: your name
 * @Description: 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
 * @FilePath: /bk-dbactuator/pkg/util/osutil/sysctl.go
 */
package osutil

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
)

// ClearTcpRecycle TODO
//
//	logger.Warn
func ClearTcpRecycle() error {
	twRecycleCmd := "grep 'net.ipv4.tcp_tw_recycle=1' /etc/sysctl.conf"
	result, err := ExecShellCommand(false, twRecycleCmd)
	if err != nil {
		err = fmt.Errorf("execute [%s] get an error:%w", twRecycleCmd, err)
		logger.Warn(err.Error())
	}
	if len(result) > 0 {
		insertTwRecycle := "sed -i -e 's/net.ipv4.tcp_tw_recycle=1/net.ipv4.tcp_tw_recycle=0/g' /etc/sysctl.conf"
		_, err := ExecShellCommand(false, insertTwRecycle)
		if err != nil {
			err = fmt.Errorf("execute [%s] get an error:%w", insertTwRecycle, err)
			logger.Info(err.Error())
			return err
		}
	}
	twReuseCmd := "grep 'net.ipv4.tcp_tw_reuse=1' /etc/sysctl.conf"
	result, err = ExecShellCommand(false, twReuseCmd)
	if err != nil {
		err = fmt.Errorf("execute [%s] get an error:%w", twReuseCmd, err)
		logger.Warn(err.Error())
	}
	if len(result) > 0 {
		insertTwReuse := "sed -i -e 's/net.ipv4.tcp_tw_reuse=1/net.ipv4.tcp_tw_reuse=0/g' /etc/sysctl.conf"
		_, err := ExecShellCommand(false, insertTwReuse)
		if err != nil {
			err = fmt.Errorf("execute [%s] get an error:%w", insertTwReuse, err)
			logger.Info(err.Error())
			return err
		}
	}

	// Linux kernel 那边只有 t-linux2-0044 开始才支持上面的 2 个参数，下面执行报错的话，给出一个warning。
	_, err = ExecShellCommand(false, "/sbin/sysctl -p")
	if err != nil {
		err = fmt.Errorf("execute [/sbin/sysctl -p] get an error:%w", err)
		logger.Warn(err.Error())
	}
	return nil
}
